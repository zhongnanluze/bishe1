"""
pydantic 模型结构化
"""
from my_llm import model
from pydantic import BaseModel ,Field

class Movie(BaseModel):
    title: str = Field(description="电影标题")
    year: int =  Field(description="电影上映年份")
    director: str = Field(description="电影导演")


model_1=model.with_structured_output(Movie)
prompt="""请介绍一下电影《肖申克的救赎》
"""
res = model_1.invoke(prompt)
print(res)



# from my_llm import model
# from pydantic import BaseModel, Field
# from typing import Optional
#
#
# # 定义电影结构化数据模型
# class Movie(BaseModel):
#     title: str = Field(description="电影标题")
#     year: int = Field(description="电影上映年份，必须是整数")
#     director: str = Field(description="电影导演")
#
#
# # 1. 创建带结构化输出的模型实例（关键：要用这个实例调用）
# model_with_struct = model.with_structured_output(Movie)
# # 2. 优化提示词，明确要求返回结构化信息
# prompt = """请按照指定结构返回电影《肖申克的救赎》的信息：
# - title：电影标题
# - year：上映年份（整数）
# - director：导演
# """
# res = model_with_struct.invoke(prompt)
#
# print(res)
#
