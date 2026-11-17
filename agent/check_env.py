# 自检程序
import sys
from importlib.metadata import version

# 实际导入，检查依赖能否正常加载
import langchain
import mcp
import dotenv


def main():
    # 防止误用系统 Python
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("请使用 agent/.venv 中的 Python 运行")

    # 显示当前使用的解释器
    print("Python 路径：", sys.executable)

    # 显示安装的依赖版本，方便后续排查兼容问题
    for package in ("langchain", "mcp", "python-dotenv"):
        print(f"{package}：{version(package)}")

    print("环境自检通过；尚未连接大模型。")


if __name__ == "__main__":
    main()