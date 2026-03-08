
from ..my_llm import model
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取指定区域天气（工具函数描述，会被LLM识别）"""
    return f"{city}的天气是好的"

# 给模型绑定自定义工具
model_bind_tool = model.bind_tools([get_weather])

# 调用模型并查询天气
resp = model_bind_tool.invoke("北京的天气怎么样")

for tool_call in resp.tool_calls:
    if tool_call['name'] == "get_weather":
        tool_result = get_weather.invoke(tool_call)
        print(tool_result)