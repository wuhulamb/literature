"""数据结构定义"""

from pydantic import BaseModel, Field


class PaperInfo(BaseModel):
    """LLM 从论文中提取的结构化信息（不含 tags：tags 由用户手动编辑 meta.json 维护）"""

    year: str = Field(description="论文发表年份，格式为YYYY，无法提取时返回\"unknown\"")  # 声明为 str，避免生成 anyOf 联合类型，保证约束解码稳定
    source: str = Field(description="论文发表的期刊或会议名称，无法提取时返回\"unknown\"")
    title: str = Field(description="论文的完整标题，无法提取时返回\"unknown\"")
    authors: list[str] = Field(description="论文的作者列表，无法提取时返回[\"unknown\"]")
    keywords: list[str] = Field(description="论文的关键词列表，3-5个，无法提取时返回[\"unknown\"]")