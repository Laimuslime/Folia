"""
Wikidot Module System for Folia.

Modules are the core building blocks of Wikidot pages.
They are invoked via [[module ModuleName param1="value1"]] syntax.
"""
import re
from typing import Any


class ModuleRegistry:
    _modules: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(module_class):
            cls._modules[name.lower()] = module_class
            return module_class
        return decorator

    @classmethod
    def get(cls, name: str):
        return cls._modules.get(name.lower())

    @classmethod
    def render(cls, name: str, params: dict, context: dict) -> str:
        module_class = cls.get(name)
        if not module_class:
            return f'<div class="error-block">模块 "{name}" 不存在。</div>'
        module = module_class(params, context)
        try:
            return module.render()
        except Exception as e:
            return f'<div class="error-block">模块 "{name}" 出错：{e}</div>'


class BaseModule:
    def __init__(self, params: dict, context: dict):
        self.params = params
        self.context = context
        self.site = context.get("site")
        self.page = context.get("page")
        self.user = context.get("user")

    def render(self) -> str:
        raise NotImplementedError

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


from . import standard  # noqa: F401
from . import listpages  # noqa: F401


def parse_module_invocation(text: str) -> tuple[str, dict] | None:
    match = re.match(r'\[\[module\s+(\w+)(.*?)\]\]', text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    name = match.group(1)
    params_str = match.group(2).strip()
    params = {}
    for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', params_str):
        params[m.group(1)] = m.group(2)
    return name, params
