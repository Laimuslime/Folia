"""
YunGouOS 支付集成
文档：https://open.pay.yungouos.com
"""
import hashlib
import requests
from django.conf import settings

WXPAY_API = "https://api.pay.yungouos.com/api/pay/wxpay/cashierPay"
ALIPAY_API = "https://api.pay.yungouos.com/api/pay/alipay/cashierPay"


def sign(params: dict, key: str) -> str:
    filtered = {k: v for k, v in params.items() if v not in ("", None) and k != "sign"}
    sorted_str = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))
    sorted_str += f"&key={key}"
    return hashlib.md5(sorted_str.encode()).hexdigest().upper()


def create_order(trade_no: str, amount: int, title: str, notify_url: str, channel: str = "wechat") -> dict:
    total_fee = f"{amount / 100:.2f}"

    params = {
        "out_trade_no": trade_no,
        "total_fee": total_fee,
        "mch_id": settings.YUNGOUOS_MCH_ID,
        "body": title,
    }
    params["sign"] = sign(params, settings.YUNGOUOS_KEY)

    params["notify_url"] = notify_url

    api_url = WXPAY_API if channel == "wechat" else ALIPAY_API
    resp = requests.post(api_url, data=params, timeout=10)
    result = resp.json()

    if result.get("code") != 0:
        return {"errcode": -1, "errmsg": result.get("msg", "支付接口错误")}

    return {
        "errcode": 0,
        "url_qrcode": result.get("data", ""),
        "url": result.get("data", ""),
    }


def verify_callback(params: dict) -> bool:
    received_sign = params.get("sign", "")
    check_params = {
        "code": params.get("code", ""),
        "orderNo": params.get("orderNo", ""),
        "outTradeNo": params.get("outTradeNo", ""),
        "payNo": params.get("payNo", ""),
        "money": params.get("money", ""),
        "mchId": params.get("mchId", ""),
    }
    expected_sign = sign(check_params, settings.YUNGOUOS_KEY)
    return received_sign == expected_sign
