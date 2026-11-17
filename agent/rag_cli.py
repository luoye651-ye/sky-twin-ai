"""Prepare/build/search local RAG without invoking DeepSeek or reading a platform token."""
import argparse
import json

from rag import KnowledgeError, KnowledgeIndex, build_index, prepare_model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "build", "search"])
    parser.add_argument("--query", help="检索问题，search时必填")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            prepare_model()
            print("中文Embedding模型已下载并通过SHA-256校验。")
        elif args.action == "build":
            print(f"知识索引已构建：{build_index()}段。")
        else:
            if not args.query:
                parser.error("search需要--query")
            matches = KnowledgeIndex().search(args.query)
            print(json.dumps({"matches": matches, "note": "仅检索证据；相似度不是检测精度或答案置信度。"}, ensure_ascii=False, indent=2))
        return 0
    except KnowledgeError as error:
        print(str(error))
    except Exception:
        print("本地模型/索引操作未完成，请检查依赖、模型文件和网络；不要输出密钥或令牌。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
