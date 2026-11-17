"""Read-only Java adapter. Credentials are never tool arguments or output."""
import os
from pathlib import Path

import httpx
from dotenv import dotenv_values
from pydantic import BaseModel, Field, FiniteFloat, ValidationError

AIRCRAFT_URL = "http://127.0.0.1:8081/sky/aircraft"
ENV_FILE = Path(__file__).resolve().parent / ".env"


class SkyReadError(RuntimeError):
    """Safe, user-facing error; contains no credentials or raw responses."""


class AircraftView(BaseModel):
    id: str = Field(min_length=1)
    name: str
    type: str
    model: str
    status: str
    battery: FiniteFloat = Field(ge=0, le=100)
    payloadCapacity: FiniteFloat = Field(ge=0)
    seats: int = Field(ge=0)


def get_platform_token() -> str:
    # An explicit empty environment value must not fall back to a different identity.
    value = os.environ.get("SKYTWIN_TOKEN")
    if value is None:
        value = dotenv_values(ENV_FILE).get("SKYTWIN_TOKEN", "")
    token = (value or "").strip()
    if not token:
        raise SkyReadError("未配置 SKYTWIN_TOKEN：请在 agent/.env 追加平台登录令牌，不是DeepSeek密钥。")
    if token.lower().startswith("bearer ") or "\r" in token or "\n" in token:
        raise SkyReadError("SKYTWIN_TOKEN只填写令牌值，不加Bearer前缀，不包含换行。")
    return token


def get_aircraft() -> list[dict]:
    """Query one fixed endpoint with the configured platform user's identity."""
    token = get_platform_token()
    try:
        response = httpx.get(
            AIRCRAFT_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            trust_env=False,
            follow_redirects=False,
        )
    except httpx.TimeoutException:
        raise SkyReadError("Java查询超时，请检查本地8081服务。") from None
    except httpx.HTTPError:
        raise SkyReadError("无法连接本地Java服务，请检查8081端口及服务状态。") from None

    if response.status_code in (401,403):
        raise SkyReadError("平台登录失效或无sky:read权限，请重新登录并更新SKYTWIN_TOKEN。")
    if response.status_code != 200:
        raise SkyReadError(f"Java HTTP状态异常：{response.status_code}；未执行任何业务写操作。")
    try:
        payload = response.json()
    except ValueError:
        raise SkyReadError("Java返回的内容不是有效JSON。") from None
    if not isinstance(payload,dict):
        raise SkyReadError("Java响应格式异常，应为包含code和data的对象。")
    code = payload.get("code")
    if not isinstance(code,int) or isinstance(code,bool):
        raise SkyReadError("Java响应code应为整数。")
    if code != 200:
        raise SkyReadError(f"Java拒绝查询，业务码{code}；请检查登录状态及sky:read权限。")
    rows = payload.get("data")
    if not isinstance(rows,list):
        raise SkyReadError("Java响应data应为飞行器列表。")
    try:
        # Only these fields leave the adapter; extra response fields are discarded.
        return [AircraftView.model_validate(row).model_dump() for row in rows]
    except ValidationError:
        raise SkyReadError("Java返回的飞行器字段或数值不符合约定。") from None


def main():
    try:
        rows = get_aircraft()
    except SkyReadError as error:
        print(str(error))
        raise SystemExit(1) from None
    print("飞行器数量：",len(rows))
    for row in rows:
        print(row["id"],row["name"],row["status"],f"电量 {row['battery']}%")


if __name__ == "__main__": main()
