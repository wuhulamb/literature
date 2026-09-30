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
export CHATECNU_API_KEY=...    # 或复制 .env.example 为 .env 并填入
```

## 命令

```bash
lit import                                # 将 inbox/ 中的 PDF 导入
lit import --tag 跨区域投资                # 导入，并为本批文献统一添加标签“跨区域投资”
lit list                                  # 列出所有文献（一张大表，tags 列展示分类）
lit list --tag 跨区域投资                  # 只列出带有标签“跨区域投资”的文献（序号与全局一致）
lit tags                                  # 列出所有标签及对应文献数（按文献数降序）
lit search --year 2017                    # 按年份精确筛选
lit search --source NeurIPS               # 按来源（期刊/会议）精确筛选
lit search --author Vaswani               # 按作者精确筛选
lit search --keyword transformer          # 对标题/作者/来源/关键词包含匹配
lit search --year 2021 --tag 跨区域投资    # 组合筛选：年份 + 标签
lit read PAPER                          # 打印 metadata + 尝试打开 paper.pdf
lit note PAPER                          # 用 $EDITOR（默认 vim）编辑 notes.md
lit remove PAPER                        # 删除已导入文献所在目录（不可逆）
```
