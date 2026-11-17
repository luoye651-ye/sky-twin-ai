from llm_client import create_llm


def main():
    # 使用公共函数创建模型客户端
    llm = create_llm()

    # 测试程序只负责准备消息和发送请求
    messages = [
        (
            "system",
            "你是SkyTwin低空管理平台的助手。"
            "当前没有连接任何业务工具，不能声称已查询或操作系统。",
        ),
        (
            "human",
            "用两句话介绍你能如何协助无人机任务管理。",
        ),
    ]

    try:
        response = llm.invoke(messages)
    except Exception as error:
        print("调用失败，错误类型：", type(error).__name__)
        print("HTTP状态：", getattr(error, "status_code", "无"))
        raise SystemExit(1) from None

    print("模型：", llm.model_name)
    print("回复：")
    print(response.content)


if __name__ == "__main__":
    main()