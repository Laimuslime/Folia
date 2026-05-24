# Folia — 维基农场 (Wiki Farm)

开源维基农场平台 — Wikidot 的完整替代方案。

## 功能

- **完整 Wikidot 语法支持** — 粗体、斜体、链接、代码块、表格、折叠块、Tab视图、脚注等
- **模块系统** — ListPages、Rate、TagCloud、PageTree、Backlinks、RecentChanges、Gallery 等
- **Include 系统** — 页面嵌入，支持参数传递
- **多站点托管** — 子域名路由，每个站点独立权限/主题/设置
- **论坛系统** — 分组、分类、帖子、嵌套回复、每页讨论
- **评分系统** — +/- 投票
- **版本历史** — 完整修订记录、差异对比
- **文件管理** — 页面附件、图片上传
- **权限系统** — 站点级、分类级权限控制
- **用户系统** — 注册、登录、JWT、站点成员管理
- **全文搜索** — Meilisearch 集成
- **AJAX 模块连接器** — 动态模块加载（兼容 Wikidot 前端架构）
- **系统页面** — list-all-pages、recent-changes、members、page-tags
- **迁移工具** — 从 Wikidot API 抓取 + XML 备份文件导入

## 快速开始

```bash
# 启动所有服务
docker-compose up -d

# 数据库迁移
docker-compose exec web python manage.py migrate

# 创建超级管理员
docker-compose exec web python manage.py createsuperuser

# 初始化数据（许可证、主题、可选 demo 站点）
docker-compose exec web python manage.py setup_initial_data --demo

# 重建搜索索引
docker-compose exec web python manage.py reindex

# 访问
# 农场首页: http://www.folia.localhost
# Demo站点: http://demo.folia.localhost
# API: http://localhost:8000/api/v1/
# 管理后台: http://localhost:8000/admin/
```

## 架构

```
Folia/
├── backend/          # Django 5 + DRF — API 和业务逻辑
│   └── folia/
│       ├── api/          # URL 路由、AJAX 模块连接器
│       ├── users/        # 用户模型、认证
│       ├── sites/        # 站点管理、成员、权限
│       ├── wiki/         # 页面、解析器、模块系统、搜索
│       └── forums/       # 论坛系统
├── frontend/         # SvelteKit 5 — Wikidot 风格前端
│   └── src/
│       ├── lib/
│       │   ├── api.ts           # API 客户端
│       │   ├── wikidot.ts       # 客户端交互（折叠、Tab）
│       │   └── components/      # 页面组件
│       └── routes/              # SvelteKit 路由
├── migration/        # 迁移工具 CLI
├── wikidot-source/   # Wikidot 原始源码（参考）
├── docker/           # Docker 配置
└── docker-compose.yml
```

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.12 + Django 5 + DRF |
| 前端 | TypeScript + Svelte 5 + SvelteKit |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 搜索 | Meilisearch |
| 存储 | MinIO (S3 兼容) |
| 解析器 | Python Wikidot 语法解析器 |

## API 端点

```
GET/POST /api/v1/sites/                    # 站点列表/创建
GET      /api/v1/sites/{slug}/             # 站点详情
GET      /api/v1/sites/{slug}/members/     # 成员列表
GET/PUT  /api/v1/sites/{slug}/settings/    # 站点设置
POST     /api/v1/sites/{slug}/join/        # 加入站点
POST     /api/v1/sites/{slug}/leave/       # 离开站点

GET/POST /api/v1/pages/                    # 页面列表/创建
GET/PUT  /api/v1/pages/{slug}/             # 页面详情/编辑
DELETE   /api/v1/pages/{slug}/             # 删除页面
GET      /api/v1/pages/{slug}/revisions/   # 修订历史
POST     /api/v1/pages/{slug}/vote/        # 投票
GET/POST /api/v1/pages/{slug}/files/       # 文件管理
POST     /api/v1/pages/{slug}/lock/        # 编辑锁

GET      /api/v1/forum/groups/             # 论坛分组
GET/POST /api/v1/forum/threads/            # 帖子列表/创建
GET      /api/v1/forum/threads/{id}/posts/ # 帖子回复
POST     /api/v1/forum/posts/              # 发表回复

POST     /api/v1/ajax-module-connector/    # AJAX 模块加载
GET      /api/v1/system/{page}/            # 系统页面
GET      /api/v1/search/?q=               # 全文搜索

POST     /api/v1/auth/register/            # 注册
POST     /api/v1/auth/token/               # 登录 (JWT)
POST     /api/v1/auth/token/refresh/       # 刷新 Token
GET      /api/v1/auth/profile/             # 当前用户
```

## 迁移工具

```bash
cd migration && pip install -e .

# 从 Wikidot API 迁移
folia-migrate api --site scp-wiki --api-key YOUR_KEY --target http://localhost:8000

# 从备份文件迁移
folia-migrate backup --file backup.xml --target http://localhost:8000

# 验证迁移结果
folia-migrate verify --site scp-wiki --target http://localhost:8000
```

## Wikidot 语法示例

```
+ 一级标题
++ 二级标题

**粗体** //斜体// __下划线__ --删除线--

[[[page-name | 链接文字]]]
[https://example.com 外部链接]

[[image filename.jpg]]

[[collapsible show="+ 展开" hide="- 收起"]]
隐藏内容
[[/collapsible]]

[[tabview]]
[[tab 标签一]]
内容一
[[/tab]]
[[tab 标签二]]
内容二
[[/tab]]
[[/tabview]]

[[module ListPages category="blog" order="created_at desc" limit="10"]]
%%title_linked%% — %%created_at%%
[[/module]]

[[module Rate]]

[[include component:info-box | title=标题 | content=内容]]
```

## 开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_initial_data --demo
python manage.py runserver

# 前端
cd frontend
npm install
npm run dev
```

## 许可证

AGPL-3.0