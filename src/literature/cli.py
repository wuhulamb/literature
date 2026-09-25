"""lit 命令行入口

用法:
  lit import                      # 将 inbox/ 中的文献导入
  lit list                        # 列出所有文献（一张大表）
  lit search [--year] [--source] [--author] [--keyword]
  lit read  PAPER                 # 查看 metadata 并尝试打开 PDF
  lit note PAPER                  # 编辑 notes.md
"""

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from . import storage, ui
from .importer import import_pdfs

load_dotenv()

app = typer.Typer(
    help="lit —— 本地 PDF 文献管理工具（数据目录: ./literature/）",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def resolve_paper(paper: str) -> Path:
    """解析 PAPER 参数：序号（与 lit list 显示的编号一致）或 目录名/路径"""
    # 序号与 lit list / lit search 一致：都以 storage.list_papers()（目录名排序）
    # 的 1-based 位置编号（见 storage.paper_at_number 与 ui.print_paper_list）
    if paper.isdigit():
        paper_dir = storage.paper_at_number(int(paper))
        if paper_dir is not None:
            return paper_dir
        n = len(storage.list_papers())
        typer.echo(f"错误：序号 {paper} 无效（共 {n} 篇文献，请输入 1-{n}，可用 `lit list` 查看）", err=True)
        raise typer.Exit(code=1)
    resolved = storage.resolve_paper(paper)
    if resolved is None:
        typer.echo(f"错误：未找到文献 '{paper}'", err=True)
        fuzzy = [p.name for p in storage.list_papers() if paper.lower() in p.name.lower()]
        if fuzzy:
            typer.echo("你可能想找:")
            for name in fuzzy[:5]:
                typer.echo(f"  - {name}")
        raise typer.Exit(code=1)
    return resolved


@app.command("import")
def import_command() -> None:
    """将 inbox/ 中的 PDF 文献导入"""
    import_pdfs()


@app.command()
def list() -> None:
    """列出所有文献（一张大表，tags 列展示分类）"""
    storage.ensure_dirs()
    ui.print_paper_list(storage.list_papers())


@app.command()
def search(
    year: Optional[str] = typer.Option(None, "--year", help="按年份精确筛选（如 2017）"),
    source: Optional[str] = typer.Option(None, "--source", help="按来源精确筛选（期刊/会议）"),
    author: Optional[str] = typer.Option(None, "--author", help="按作者精确筛选"),
    keyword: Optional[str] = typer.Option(None, "--keyword", help="对标题/作者/来源/关键词做包含匹配"),
) -> None:
    """搜索文献（year / source / author / keyword）"""
    papers = storage.filter_papers(
        year=year, source=source, author=author, keyword=keyword
    )
    typer.echo(f"匹配到 {len(papers)} 篇文献:")
    ui.print_paper_list(papers)


@app.command()
def read(paper: str = typer.Argument(..., help="文献序号（lit list 显示的编号）或目录名/路径")) -> None:
    """查看 metadata，并尝试打开 paper.pdf"""
    storage.ensure_dirs()
    paper_dir = resolve_paper(paper)
    ui.show_meta(paper_dir)
    ui.open_pdf(paper_dir)


@app.command()
def note(paper: str = typer.Argument(..., help="文献序号（lit list 显示的编号）或目录名/路径")) -> None:
    """用 $EDITOR（默认 vim）编辑 notes.md"""
    storage.ensure_dirs()
    paper_dir = resolve_paper(paper)
    ui.open_notes(paper_dir)


if __name__ == "__main__":
    app()