"""文件系统存储层：目录结构、meta.json、文件名规范、hash 去重"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import PaperInfo

MAX_DIRNAME_LENGTH = 120  # 目录名最大长度（字符）
DIRNAME_SEPARATOR = "_"

# 数据根目录固定在运行目录下（不支持环境变量配置）
DATA_DIR = Path("literature")
PAPERS_DIR = DATA_DIR / "papers"
INBOX_DIR = DATA_DIR / "inbox"

_ILLEGAL_CHARS = re.compile(r'[\\/*?:"<>|\'“”‘’]')


def ensure_dirs() -> None:
    """确保数据目录结构存在"""
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """清理文件/目录名中的非法字符"""
    return _ILLEGAL_CHARS.sub("", name)


def build_dirname(info: PaperInfo) -> str:
    """根据元数据派生目录名 {year}_{source}_{first_author}_{title}

    最大长度 120 字符，超长时保留 年份/source/作者，只截断 title。
    """
    first_author = info.authors[0] if info.authors else "unknown"
    name = f"{info.year}{DIRNAME_SEPARATOR}{info.source}{DIRNAME_SEPARATOR}{first_author}{DIRNAME_SEPARATOR}{info.title}"
    name = sanitize_filename(name).strip(" .")

    if len(name) <= MAX_DIRNAME_LENGTH:
        return name

    prefix = sanitize_filename(
        f"{info.year}{DIRNAME_SEPARATOR}{info.source}{DIRNAME_SEPARATOR}{first_author}{DIRNAME_SEPARATOR}"
    )
    title_room = MAX_DIRNAME_LENGTH - len(prefix)
    title = sanitize_filename(info.title).strip(" .")[:title_room]
    return prefix + title


def file_sha256(path: Path) -> str:
    """计算文件 sha256，带算法前缀存于 meta.json"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def list_papers() -> list[Path]:
    """返回所有已导入论文目录（按目录名排序）"""
    if not PAPERS_DIR.exists():
        return []
    return sorted(p for p in PAPERS_DIR.iterdir() if p.is_dir())


def paper_at_number(number: int) -> Optional[Path]:
    """按全局编号取论文目录：编号 = list_papers()（目录名排序）的 1-based 位置

    lit list / lit search 表格显示的编号与 lit read/note <数字> 的序号解析
    共用这一排序，保证两边编号一致。
    """
    papers = list_papers()
    if 1 <= number <= len(papers):
        return papers[number - 1]
    return None


def load_meta(paper_dir: Path) -> Optional[dict]:
    """读取论文目录下的 meta.json（旧数据兼容：缺省字段补默认值）"""
    meta_path = paper_dir / "meta.json"
    if not meta_path.exists():
        return None
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    meta.setdefault("tags", [])
    meta.setdefault("authors", [])
    meta.setdefault("keywords", [])
    return meta


def write_meta(paper_dir: Path, info: PaperInfo, file_hash: str) -> None:
    """写入 meta.json（唯一 metadata 来源，不含论文正文）

    tags 不由 LLM 生成，由用户手动编辑 meta.json 维护，导入时置空。
    """
    meta = {
        "year": info.year,
        "source": info.source,
        "title": info.title,
        "authors": info.authors,
        "first_author": info.authors[0] if info.authors else "unknown",
        "keywords": info.keywords,
        "tags": [],  # 手动维护：编辑 meta.json 的 tags 数组即可，空数组=未分类
        "hash": file_hash,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(paper_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def existing_hashes() -> set[str]:
    """所有已导入论文的 hash 集合，用于重复导入检测"""
    hashes = set()
    for d in list_papers():
        meta = load_meta(d) or {}
        if meta.get("hash"):
            hashes.add(meta["hash"])
    return hashes


def paper_tags(paper_dir: Path) -> list[str]:
    """某篇论文的 tags（无 tags 字段时返回空列表）"""
    meta = load_meta(paper_dir) or {}
    return [t for t in meta.get("tags", []) if t]


def resolve_paper(identifier: str) -> Optional[Path]:
    """按 目录名 / 相对路径 解析论文目录（序号解析见 paper_at_number）"""
    # 完整路径
    p = Path(identifier)
    if p.is_dir() and (p / "meta.json").exists():
        return p
    # papers 目录下的相对路径或目录名
    candidate = PAPERS_DIR / identifier
    if candidate.is_dir():
        return candidate
    # 目录名包含匹配，唯一命中时返回
    papers = list_papers()
    matches = [d for d in papers if identifier in d.name]
    if len(matches) == 1:
        return matches[0]
    return None


def filter_papers(
    year: Optional[str] = None,
    source: Optional[str] = None,
    author: Optional[str] = None,
    keyword: Optional[str] = None,
) -> list[Path]:
    """按条件筛选文献

    --year/--source/--author 精确筛选；--keyword 对 meta.json 的
    title/source/authors/keywords 做包含匹配。
    """
    result: list[Path] = []
    for d in list_papers():
        meta = load_meta(d) or {}

        if year and str(meta.get("year", "")) != year:
            continue
        if source and str(meta.get("source", "")).lower() != source.lower():
            continue
        if author:
            authors = [a.lower() for a in meta.get("authors", [])]
            if author.lower() not in authors:
                continue
        if keyword:
            k = keyword.lower()
            haystack = " ".join(
                [
                    str(meta.get("title", "")),
                    str(meta.get("source", "")),
                    " ".join(meta.get("authors", [])),
                    " ".join(meta.get("keywords", [])),
                ]
            ).lower()
            if k not in haystack:
                continue

        result.append(d)
    return result