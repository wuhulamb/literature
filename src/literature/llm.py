"""调用 ECNU LLM 提取论文元数据（按官方文档规范）"""

import json
import os
from typing import Optional

from openai import OpenAI

from .models import PaperInfo

API_BASE_URL = "https://chat.ecnu.edu.cn/open/api/v1"
MODEL = "ecnu-plus"  # 官方文档声明仅 ecnu-plus / ecnu-max 支持结构化输出
MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "你是一个专业的学术助手。"
    "请严格按照以下 JSON 格式输出，不要添加任何列表、序号、注释、说明或额外文本：\n"
    "{\n"
    "  \"year\": \"2006\",\n"
    "  \"source\": \"期刊或会议名称\",\n"
    "  \"title\": \"论文标题\",\n"
    "  \"authors\": [\"作者1\", \"作者2\"],\n"
    "  \"keywords\": [\"关键词1\", \"关键词2\"]\n"
    "}\n"
    "仅输出合法 JSON。如果某个字段无法从论文内容中提取，"
    "则使用 \"unknown\" 填充（year 字段也填充为字符串 \"unknown\"，"
    "authors 和 keywords 字段填充为 [\"unknown\"]）。"
)


def _build_client() -> Optional[OpenAI]:
    """从环境变量构建 OpenAI 兼容客户端"""
    api_key = os.getenv("CHATECNU_API_KEY")
    if not api_key:
        print("错误：未找到环境变量 CHATECNU_API_KEY，请在 .env 文件中设置")
        return None
    return OpenAI(api_key=api_key, base_url=API_BASE_URL)


def extract_publication_info(
    page_text: str,
) -> Optional[PaperInfo]:
    """从论文文本（前几页）提取年份、来源、标题、作者、关键词

    使用 json_schema 结构化输出，失败自动重试，超过 MAX_RETRIES 返回 None。
    （tags 不在提取范围内：分类由用户手动编辑 meta.json 维护）
    """
    client = _build_client()
    if client is None:
        return None

    user_prompt = f"请提取以下论文的信息：\n\n{page_text}"
    json_schema = json.dumps(PaperInfo.model_json_schema())

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"正在调用AI API提取论文信息 (第 {attempt}/{MAX_RETRIES} 次)...")

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # 官方文档示例推荐取值
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "foo", "schema": json.loads(json_schema)},
                },
                max_tokens=1024,
            )

            parsed = json.loads(response.choices[0].message.content)
            return PaperInfo(**parsed)

        except Exception as e:
            print(f"错误：提取信息时发生错误: {e}")
            continue

    print(f"错误：提取论文信息失败，已达到最大重试次数 {MAX_RETRIES}")
    return None