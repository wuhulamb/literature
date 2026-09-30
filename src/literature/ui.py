"""终端显示"""

import os
import shlex
import subprocess
import sys
from pathlib import Path

from rich import box
from rich.cells import cell_len
from rich.console import Console
from rich.table import Table

from . import storage


def _paper_row(index: int, paper_dir: Path) -> tuple[str, str, str, str, str, str]:
    """论文表格一行：[编号, 年份, 来源, 第一作者, 标题, tags]（全部转 str）"""
    meta = storage.load_meta(paper_dir) or {}
    tags = ", ".join(storage.paper_tags(paper_dir)) or "未分类"
    return (
        f"[{index}]",
        str(meta.get("year", "?")),
        str(meta.get("source", "?")),
        str(meta.get("first_author", "?")),
        str(meta.get("title", "?")),
        tags,
    )


def _paper_table(
    rows: list[tuple[str, str, str, str, str, str]], show_edge: bool = True
) -> Table:
    """rich 表格：编号|年份|来源|第一作者|标题|tags

    box.MINIMAL 只画竖向分隔线，轻量且分组清晰；编号右对齐、青色。
    show_edge=False 时去掉顶/底边框，使非 TTY（管道）输出每行即一条文献。
    """
    table = Table(
        show_header=False,
        box=box.MINIMAL,
        show_edge=show_edge,
        pad_edge=False,
        expand=False,
        safe_box=False,
        padding=(0, 1),
    )
    table.add_column(justify="right", style="cyan", no_wrap=True)  # 编号
    for _ in range(4):
        table.add_column(no_wrap=True)  # 年份 / 来源 / 第一作者 / 标题
    table.add_column(no_wrap=True)  # tags
    for row in rows:
        table.add_row(*row)
    return table


def _truncate(s: str, width: int) -> str:
    """按显示宽度（中文全角按 2 列）截断并追加省略号"""
    if width <= 0:
        return ""
    if cell_len(s) <= width:
        return s
    keep = width - 1  # 留 1 列给省略号
    result = ""
    cur = 0
    for ch in s:
        w = cell_len(ch)
        if cur + w > keep:
            break
        result += ch
        cur += w
    return result + "…"


# rich 表格固定开销：MINIMAL 左右边框 2 + 内部竖线 (6-1) + 每列 padding 2*6
_TABLE_OVERHEAD = 2 + 5 + 12
def _fit_widths(cw: list[int], avail: int) -> list[int]:
    """在可用宽度内分配 6 列展示宽：固定列先按上限收缩，富余宽度全部给标题(索引4)

    cw: 各列内容最大显示宽；avail: 去除边框/竖线/padding 后可用的内容宽度。
    保证六列总宽 ≤ avail，表格不会超出终端。
    """
    caps = (5, 5, 32, 20, 10**9, 36)  # 每列上限（标题不限）
    floor = (5, 5, 12, 12, 8, 12)  # 各列可收缩下限
    w = [min(c, cw[i]) for i, c in enumerate(caps)]
    total = sum(w)
    if total <= avail:
        w[4] = min(cw[4], w[4] + (avail - total))  # 富余给标题
        return w
    for idx in (2, 3, 5):  # 先收缩 来源/作者/tags
        while w[idx] > floor[idx] and total > avail:
            w[idx] -= 1
            total -= 1
    while w[4] > floor[4] and total > avail:  # 再收缩标题
        w[4] -= 1
        total -= 1
    while w[4] > 0 and total > avail:  # 极端窄终端兜底
        w[4] -= 1
        total -= 1
    if total < avail:  # 收缩后富余仍回补标题
        w[4] = min(cw[4], w[4] + (avail - total))
    return w


def _render_papers(rows: list[tuple[str, str, str, str, str, str]]) -> None:
    """渲染论文表：TTY 下自适应终端宽度，超宽列截断加省略号；管道/重定向输出完整内容。

    rich 在渲染宽度不足且列 no_wrap 时会丢弃左侧列（rich 15 布局缺陷），
    本实现先手动将各列截断到终端可容纳的宽度（总宽 ≤ 终端宽），再按该宽度渲染，
    因此不会触发丢列，也不会超出终端导致折回。
    """
    widths = [max(cell_len(r[i]) for r in rows) for i in range(6)]
    if sys.stdout.isatty():
        import shutil

        term_w = shutil.get_terminal_size((80, 24)).columns
        fitted = _fit_widths(widths, term_w - _TABLE_OVERHEAD)
        rows = [tuple(_truncate(c, fitted[i]) for i, c in enumerate(r)) for r in rows]
        Console(width=term_w).print(_paper_table(rows))
    else:
        # 非 TTY：不截断，按内容宽度完整输出；隐藏顶/底边框，使每行即一条文献
        req = sum(widths) + (len(widths) - 1) * 3 + 4
        Console(width=req).print(_paper_table(rows, show_edge=False))


def print_paper_list(papers: list[Path]) -> None:
    """打印文献列表（全部论文一张大表：编号/年份/来源/作者/标题/tags）

    编号取全局唯一编号：list_papers()（目录名排序）的 1-based 位置，
    与 `lit read/note <数字>` 的序号解析共用同一排序（storage.paper_at_number）。
    """
    if not papers:
        print("（没有匹配的文献）")
        return
    global_index = {d: i + 1 for i, d in enumerate(storage.list_papers())}
    rows = [_paper_row(global_index[d], d) for d in papers]
    _render_papers(rows)


def print_tag_list(tags: list[tuple[str, int]]) -> None:
    """打印所有标签及文献数（tag | 数量）

    TTY 下显示上下边框；管道/重定向时隐藏顶/底边框，每行一个标签，
    便于 `lit tags | wc -l` 直接得到标签数。
    """
    if not tags:
        print("（没有任何标签）")
        return
    table = Table(
        show_header=False,
        box=box.MINIMAL,
        show_edge=sys.stdout.isatty(),
        pad_edge=False,
        expand=False,
        safe_box=False,
        padding=(0, 1),
    )
    table.add_column(style="cyan", no_wrap=True)  # tag
    table.add_column(justify="right", no_wrap=True)  # 文献数
    for tag, n in tags:
        table.add_row(tag, str(n))
    Console().print(table)


def show_meta(paper_dir: Path) -> None:
    """打印完整 metadata"""
    print(f"论文目录: {paper_dir}/")
    meta = storage.load_meta(paper_dir)
    if meta is None:
        print("（未找到 meta.json）")
        return
    print(f"年份:     {meta.get('year', '?')}")
    print(f"来源:     {meta.get('source', '?')}")
    print(f"标题:     {meta.get('title', '?')}")
    print(f"作者:     {', '.join(meta.get('authors', []) or [])}")
    print(f"关键词:   {', '.join(meta.get('keywords', []) or [])}")
    print(f"tags:     {', '.join(meta.get('tags', []) or [])}")
    print(f"hash:     {meta.get('hash', '?')}")
    print(f"导入时间: {meta.get('imported_at', '?')}")


def open_pdf(paper_dir: Path) -> None:
    """尝试用 xdg-open 打开 PDF，失败则打印路径"""
    pdf = paper_dir / "paper.pdf"
    if not pdf.exists():
        print(f"未找到论文文件: {pdf}")
        return
    try:
        result = subprocess.run(["xdg-open", str(pdf)])
        if result.returncode != 0:
            raise OSError(f"xdg-open 返回码 {result.returncode}")
    except (OSError, FileNotFoundError) as e:
        print(f"无法打开 PDF（{e}），文件位于: {pdf}")


def open_notes(paper_dir: Path) -> None:
    """用 $EDITOR（默认 vim）打开 notes.md，不存在时懒创建"""
    notes = paper_dir / "notes.md"
    if not notes.exists():
        notes.touch()
    editor = shlex.split(os.getenv("EDITOR", "vim"))
    try:
        subprocess.run([*editor, str(notes)], check=False)
    except (OSError, FileNotFoundError) as e:
        print(f"无法启动编辑器 '{' '.join(editor)}'（{e}），笔记文件位于: {notes}")
    print(f"笔记文件: {notes}")