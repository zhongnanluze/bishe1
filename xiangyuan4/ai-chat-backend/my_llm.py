# from langchain.chat_models import init_chat_model
#
# from env_utils import *
#
# qwen_llm = init_chat_model(
#     model="qwen-turbo",
#     model_provider="deepseek",
#     api_key=ALIYUN_BAILIAN_API_KEY,
#     base_url=ALIYUN_BAILIA_BASE_URL,
#     model_name=model,
# )
#
# print(qwen_llm)
# # resp = qwen_llm.invoke("你好")
# # print(resp)


# from openai import OpenAI
#
# from env_utils import *
#
# client = OpenAI(
#     api_key=ALIYUN_BAILIAN_API_KEY,
#     base_url=ALIYUN_BAILIA_BASE_URL,
# )
#
# response = client.chat.completions.create(
#     model="qwen-plus",
#     messages=[
#         {"role": "user", "content": "你是谁。"},
#     ]
# )
# print(response.choices[0].message.content)
# print(response.model_dump_json())

from langchain_community.chat_models.tongyi import ChatTongyi
from env_utils import *
model = ChatTongyi(dashscope_api_key=ALIYUN_BAILIAN_API_KEY)

# question = "你是谁"
# result = model.invoke(question)
# print(result.content)