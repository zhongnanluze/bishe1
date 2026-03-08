from certifi import contents
from langchain_classic.agents.chat.prompt import HUMAN_MESSAGE
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from my_llm import deepseek_llm

@tool
def get_weather(city:str)->str:
    """获取城市天气"""
    return f"{city}的天气是晴天"


#绑定工具
model_bind_tool= deepseek_llm.bind_tools([get_weather])

messages = []
human_messages = HumanMessage(content="上海的天气怎么样")
messages.append(human_messages)


#llm 返回调用工具请求
ai_message = model_bind_tool.invoke(messages)
messages.append(ai_message)

for tool_call in ai_message.tool_calls:
    if tool_call['name'] == "get_weather":
        tool_result = get_weather.invoke(tool_call)
        messages.append(tool_result)

        # print(type(tool_result))
        # print(tool_result)
resp = model_bind_tool.invoke(messages)
print(messages)
print(resp)
