import os

from flask.cli import load_dotenv

load_dotenv()

ALIYUN_BAILIAN_API_KEY = os.getenv('ALIYUN_BAILIAN_API_KEY')
ALIYUN_BAILIA_BASE_URL = os.getenv('ALIYUN_BAILIA_BASE_URL')
model = os.getenv('MODEL_NAME')

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL')
