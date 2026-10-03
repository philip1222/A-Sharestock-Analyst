# 书籍 PDF 命名规则（强制）

## 目标

统一命名后，Skill 才能稳定定位到对应书籍并读取章节。

## 命名格式

`[层级]_[序号两位]_[英文短名]_[作者英文]_[版本年份可选].pdf`

示例：

- `L1_01_trade-your-way-to-financial-freedom_van-k-tharp_2009.pdf`
- `L2_06_security-analysis_graham-dodd_2008.pdf`
- `L4_16_shou-ba-shou-du-cai-bao_tangchao.pdf`

## 命名约束

- 仅使用小写英文字母、数字、连字符 `-`、下划线 `_`
- 不使用空格、中文标点、括号、特殊符号
- 序号必须与 `BOOKLIST.md` 的优先级一致
- 同书多版本时，仅在末尾追加年份或版本号

## 目录约束

所有 PDF 放入：

`references/books_pdf/`

可按层级分子目录（可选）：

- `references/books_pdf/L1/`
- `references/books_pdf/L2/`
- `references/books_pdf/L3/`
- `references/books_pdf/L4/`

## 索引校验建议

你放好文件后，可人工核对：

1. 文件名与 `BOOKLIST.md` 是否一一对应。
2. 同一本书是否只保留一个主版本（避免读取歧义）。
3. 是否存在无法识别字符（例如全角空格）。
