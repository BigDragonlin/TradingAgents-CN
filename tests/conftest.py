import os
from pathlib import Path
try:
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"

    # 打印出计算出的 .env 文件绝对路径
    print(f"Attempting to load .env file from: {env_file}")

    if env_file.exists():
        load_dotenv(env_file, override=True)
        user_name = os.getenv("EMAIL_USER")
        openai_key = os.getenv("OPENAI_API_KEY")
    else:
        # 如果文件不存在，明确地打印出来
        print(".env file NOT found at the calculated path.")

except Exception as e:
    print(f"An error occurred: {e}")

