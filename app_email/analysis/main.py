import sys
from dotenv import load_dotenv
from .logging_setup import setup_cli_logging
from .commands import main_with_args

# 加载环境变量
load_dotenv()


if __name__ == "__main__":
    setup_cli_logging()
    main_with_args()


