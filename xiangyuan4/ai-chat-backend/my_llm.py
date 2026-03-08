from langchain_deepseek import ChatDeepSeek
from env_utils import *

deepseek_llm = ChatDeepSeek(
    model="deepseek-chat",  # 必填：通用对话模型（也可填 deepseek-coder 等）
    api_key=DEEPSEEK_API_KEY,  # 正确参数名：api_key（非 deepseek_api_key）
    base_url=DEEPSEEK_BASE_URL,  # 正确参数名：base_url（非 deepseek_base_url）
    temperature=0.7,  # 可选：随机性（0-1）
    max_tokens=2048   # 可选：最大生成令牌数
)
#
# res=model.invoke("你好")
# print(res)
