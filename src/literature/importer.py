"""lit import：将 inbox/ 中的 PDF 导入为论文目录"""

import shutil
from pathlib import Path
from typing import Optional

import pymupdf

from . import storage
from .llm import extract_publication_info

FIRST_PAGES_FOR_LLM = 3  # LLM 提取 metadata 只输入前 3 页


def extract_pdf_pages(pdf_path: Path) -> Optional[list[str]]:
    """逐页提取文本，返回页文本列表；失败返回 None"""
    try:
        doc = pymupdf.open(pdf_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        if not any(p.strip() for p in pages):
            print(f"警告：PDF 内容为空或无法提取文本: {pdf_path.name}")
            return None
        return pages
    except Exception as e:
        print(f"错误：读取 PDF 失败 {pdf_path.name}: {e}")
        return None


def import_pdfs(tag: Optional[str] = None) -> None:
    """扫描 inbox/ 中的 PDF，提取元数据并导入 papers/

    tag: 可选，为这批新导入的文献统一添加的标签；自动 trim，
         空值（含仅空白）视为未指定。hash 重复或目录名冲突的
         已导入文献也会合并该标签。
    """
    storage.ensure_dirs()

    # 清洗可选 tag：trim 首尾空白，strip 后为空则视为未指定
    tag = (tag or "").strip() or None

    pdfs = sorted(storage.INBOX_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"inbox 中没有 PDF 文件: {storage.INBOX_DIR}/")
        return

    known_hashes = storage.existing_hashes()
    succeeded: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []

    print(f"开始导入 {len(pdfs)} 个 PDF 文件...\n")

    for pdf in pdfs:
        print(f"开始处理: {pdf.name}")

        # 1. hash 去重（与已导入文献 + 本批已导入的对比）
        file_hash = storage.file_sha256(pdf)
        if file_hash in known_hashes:
            if tag:
                dup_dir = storage.paper_dir_by_hash(file_hash)
                if dup_dir is not None:
                    # 不是纯跳过：把新 tag 合并进已导入文献的 meta.json
                    storage.add_tags(dup_dir, [tag])
                    print(f"重复文件（hash 已存在），已将 tag '{tag}' 合并到: {dup_dir.name}\n")
                else:
                    print(f"跳过重复文件（hash 已存在）: {pdf.name}\n")
            else:
                print(f"跳过重复文件（hash 已存在）: {pdf.name}\n")
            skipped.append(pdf.name)
            continue

        # 2. 提取全文
        pages = extract_pdf_pages(pdf)
        if pages is None:
            print(f"错误：无法提取 PDF 文本: {pdf.name}\n")
            failed.append(pdf.name)
            continue
        full_text = "\n".join(pages)

        # 3. LLM 只读前 3 页提取元数据（tags 不由 LLM 生成，仅在 --tag 指定时写入）
        info = extract_publication_info("\n".join(pages[:FIRST_PAGES_FOR_LLM]))
        if info is None:
            print(f"错误：无法提取论文信息，文件保留在 inbox: {pdf.name}\n")
            failed.append(pdf.name)
            continue

        # 4. 建目录并落地文件
        dirname = storage.build_dirname(info)
        target = storage.PAPERS_DIR / dirname
        if target.exists():
            if tag:
                # 目录名冲突：把新 tag 合并进已有文献的 meta.json
                storage.add_tags(target, [tag])
                print(f"警告：目录已存在，已将 tag '{tag}' 合并到: {dirname}\n")
            else:
                print(f"警告：目录已存在，跳过: {dirname}\n")
            skipped.append(pdf.name)
            continue

        target.mkdir(parents=True)
        shutil.move(str(pdf), target / "paper.pdf")
        (target / "paper.txt").write_text(full_text, encoding="utf-8")
        storage.write_meta(target, info, file_hash, tags=[tag] if tag else None)
        known_hashes.add(file_hash)  # 本批内也去重

        print(f"导入成功: {dirname}\n")
        succeeded.append(dirname)

    print("=" * 50)
    print("导入完成！统计结果:")
    print(f"  导入成功: {len(succeeded)} 个文件")
    print(f"  跳过重复: {len(skipped)} 个文件")
    print(f"  导入失败: {len(failed)} 个文件（保留在 inbox）")
    print("=" * 50)
    if failed:
        print("失败清单（保留在 inbox/ 未导入）:")
        for name in failed:
            print(f"  - {name}")