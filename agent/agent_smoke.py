"""Read-only aircraft and project knowledge queries; this CLI calls the paid DeepSeek API."""
import argparse
import asyncio

from aircraft_agent import AgentRunError, run_question
from rag import KnowledgeError, get_index, search_knowledge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", help="查询问题；省略后从终端输入")
    parser.add_argument("--aircraft-only", action="store_true", help="仅运行原飞行器查询，不加载知识库")
    args = parser.parse_args()
    print("只读Agent：支持飞行器查询和项目知识问答，会调用DeepSeek并消耗API额度；不支持派机或起飞。")
    try:
        question = args.question if args.question is not None else input("请输入问题：")
        if not args.aircraft_only:
            get_index()  # Check local readiness before paying for a model request.
        answer = asyncio.run(run_question(question, log=print, knowledge=None if args.aircraft_only else search_knowledge))
    except (AgentRunError, KnowledgeError) as error:
        print("未完成：", str(error))
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        return 1
    except Exception:
        print("运行环境异常；请检查Python/MCP环境，不要粘贴密钥或令牌。")
        return 1
    print(f"\n工具返回次数：{answer.tool_messages}；MCP实际查询次数：{answer.mcp_calls}")
    print(f"本地知识检索次数：{answer.knowledge_calls}")
    if answer.aircraft_count is not None:
        print(f"Java本次返回：{answer.aircraft_count}架（仿真登记数据）")
    print("Agent回复：")
    print(answer.text)
    if answer.sources:
        print("\n依据（程序核验过的检索来源，不是模型自行生成的文件名）：")
        for source in answer.sources:
            print(f"[{source['citation_id']}] {source['source']} · {source['section']} · 行{source['line_start']}～{source['line_end']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
