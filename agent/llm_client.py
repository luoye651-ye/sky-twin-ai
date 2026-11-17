import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek


def create_llm() -> ChatDeepSeek:
    """读取配置并创建模型客户端，不发送模型请求。"""

    # 根据本文件的位置，读取旁边的 .env
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path, override=False)

    # 读取配置并检查密钥是否存在
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请检查配置")

    # 将创建好的客户端交给调用者
    return ChatDeepSeek(
        model=model_name,
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0,
        max_tokens=256,
        timeout=45,
        max_retries=0,
        extra_body={"thinking": {"type": "disabled"}},
    )