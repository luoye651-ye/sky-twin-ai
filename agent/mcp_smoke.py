"""Launch the MCP server, discover its tool, and query Java; no LLM call."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from sky_client import SkyReadError, get_platform_token


def server_parameters(token: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-u",str(Path(__file__).resolve().parent / "mcp_server.py")],
        cwd=str(Path(__file__).resolve().parent),
        # The DeepSeek key is not passed to this subprocess.
        env={"SKYTWIN_TOKEN":token,"PYTHONUTF8":"1","PYTHONUNBUFFERED":"1"},
    )


async def query_mcp(token: str) -> dict:
    async with Client(server_parameters(token),read_timeout_seconds=20,cache=None) as client:
        tools = await client.list_tools()
        if {tool.name for tool in tools.tools} != {"list_aircraft"}:
            raise SkyReadError("MCP工具清单与本次只读约定不一致。")
        result = await client.call_tool("list_aircraft",{})
        if result.is_error:
            # The server adapter already sanitizes tool errors; do not dump raw protocol.
            messages = [part.text for part in result.content if part.type == "text"]
            raise SkyReadError("MCP查询失败："+" ".join(messages))
        data = result.structured_content
        if not isinstance(data,dict) or not isinstance(data.get("aircraft"),list) or data.get("count") != len(data["aircraft"]):
            raise SkyReadError("MCP返回的数据结构不正确。")
        return data


async def check_tools() -> None:
    """Verify the real stdio subprocess without credentials or an HTTP call."""
    async with Client(server_parameters(""),read_timeout_seconds=20,cache=None) as client:
        tools = await client.list_tools()
        if [tool.name for tool in tools.tools] != ["list_aircraft"]:
            raise SkyReadError("MCP工具清单与本次只读约定不一致。")
        tool = tools.tools[0]
        if not tool.annotations or not tool.annotations.read_only_hint or not tool.output_schema:
            raise SkyReadError("MCP工具缺少只读声明或结构化输出定义。")
    print("MCP stdio启动、工具发现、只读声明和结构化输出定义检查通过。")
    print("工具：list_aircraft；本次未查询Java数据。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-tools",action="store_true",help="仅验证MCP协议，不需要平台令牌")
    args = parser.parse_args()
    try:
        if args.check_tools:
            asyncio.run(check_tools())
            return
        data = asyncio.run(query_mcp(get_platform_token()))
    except SkyReadError as error:
        print(str(error))
        raise SystemExit(1) from None
    except Exception:
        print("MCP连接未完成，请检查本地服务及MCP环境；不要输出密钥或原始协议日志。")
        raise SystemExit(1) from None
    print("MCP工具：list_aircraft（只读）")
    print(json.dumps(data,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
