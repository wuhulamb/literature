# literature (lit)

本地 PDF 文献管理工具。文件系统是唯一存储层，不使用数据库。

## 数据目录结构

```
literature/
├── papers/
│   └── {year}_{source}_{first_author}_{title}/   # 目录名 ≤120 字符
│       ├── meta.json     # 唯一 metadata 来源（结构化字段，不含正文）
│       ├── paper.txt     # 从 paper.pdf 解析出的全文
│       └── paper.pdf     # 原始论文
└── inbox/                # 待导入 PDF 暂存区
```

## 快速开始

```bash
uv sync                        # 安装依赖并注册 lit 命令
export CHATECNU_API_KEY=...    # 或写入 .env（参考 .env 文件）
```

## 命令

```bash
lit import                                # 将 inbox/ 中的 PDF 导入
lit list                                  # 列出所有文献（一张大表，tags 列展示分类）
lit search --year 2017                    # 按年份精确筛选
lit search --source NeurIPS               # 按来源（期刊/会议）精确筛选
lit search --author Vaswani               # 按作者精确筛选
lit search --keyword transformer          # 对标题/作者/来源/关键词包含匹配
lit read PAPER                          # 打印 metadata + 尝试打开 paper.pdf
lit note PAPER                          # 用 $EDITOR（默认 vim）编辑 notes.md
```
