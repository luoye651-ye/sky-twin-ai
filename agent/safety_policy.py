"""Narrow deterministic disclosure policy, separate from semantic similarity."""
import re


def is_secret_request(text: str) -> bool:
    secret = re.search(r'数据库密码|账号密码|密码|API\s*密钥|密钥|登录令牌|访问令牌|api[ _-]*key|access[ _-]*token|password', text, re.I)
    disclosure = re.search(r'是多少|是什么|告诉我|给我|发给我|显示|输出|打印|泄露|读取|\b(reveal|show|print|give|send)\b|what\s+is', text, re.I)
    guidance = re.search(r'如何|怎么|怎样|how\s+(to|do|can|should)', text, re.I)
    return bool(secret and disclosure and not guidance)
