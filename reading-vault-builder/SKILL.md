---
name: reading-vault-builder
description: Use when turning a book, ebook, chapter set, PDF, epub, txt, md, or reading URL into an Obsidian reading-notes vault with chapter summaries, theme indexes, concept notes, quotes, and lightweight comprehension checks.
---

# Reading Vault Builder

把书籍资料整理成 Obsidian 风格的 `ReadingVault/`。默认目标是**读书笔记库**，不是陪读对话，也不是代码工程分析。

默认约定：

- 主输入：`PDF`、`epub`
- 次输入：`txt`、`md`、`url`
- 默认输出：中文笔记
- 保留：原文术语、关键引文
- 组织方式：章节笔记为主，主题索引为辅

所有读取和输出都限制在 CWD 内。用户给外部路径时，要求先复制到当前目录。

## 默认产物

```text
ReadingVault/
  00-Overview/
  01-Chapters/
  02-Themes/
  03-Concepts/
  04-Quotes/
  05-Checks/
```

- `00-Overview/`：全书总览、章节入口、主题入口
- `01-Chapters/`：逐章笔记，主阅读层
- `02-Themes/`：跨章节主题或母题
- `03-Concepts/`：高频概念、人物、框架
- `04-Quotes/`：可追溯引文
- `05-Checks/`：轻量理解检查

模板见 [references/templates.md](references/templates.md)。交付前按 [references/quality-checklist.md](references/quality-checklist.md) 自检。

## 提取脚本

处理 `epub` 时，优先先运行本地脚本：

```bash
python3 reading-vault-builder/scripts/extract_epub.py \
  --epub "/path/to/book.epub" \
  --out-dir "./out/epub-text"
```

默认输出：

- `metadata.json`
- `toc.json`
- `chapters.json`
- `chapters/*.txt`

后续笔记整理优先基于这些抽取结果，而不是直接在压缩包里逐个猜章节。

## 工作流

### 1. Discover

扫描并确认书籍源：

- `**/*.pdf`
- `**/*.epub`
- `**/*.txt`
- `**/*.md`
- 用户给出的 `url`

排除：

- `.git/`
- `node_modules/`
- `dist/`
- `build/`
- `ReadingVault/`

如果有多本书、多版本或多卷，先让用户确认当前处理对象。

### 2. Extract

先拿到可读文本，再分析。

- `PDF`：优先 `pdftotext`
- `epub`：优先运行 `reading-vault-builder/scripts/extract_epub.py`
- `txt` / `md`：直接读取
- `url`：只提正文，不把导航、广告、评论区当正文

先确认：

- 书名
- 作者
- 目录或章节列表
- 前言 / 正文 / 附录边界

### 3. Map Structure

先建结构地图，再写笔记。

至少完成：

1. 读封面、目录、开头
2. 抽样读中段和末段
3. 建立映射：
   - `chapter/section -> source file -> page range or anchor`
4. 没有稳定页码时，用章节锚点或标题层级
5. 材料不完整时，明确标缺失

### 4. Write Chapter Notes First

先写章节页，再写跨章节页。不要一开始就写一篇全书长总结。

每章至少包含：

- 本章摘要
- 核心观点 / 关键事件
- 关键概念 / 人物 / 场景
- 重要引文
- 与前后章节的联系
- 我的疑问
- `3-5` 个理解检查题
- `## Related Notes`

### 5. Build Cross-Chapter Pages

在章节页稳定后再生成：

- `00-Overview/全书总览.md`
- `02-Themes/`：只收跨章节主题
- `03-Concepts/`：只收值得反复引用的概念、人物、框架
- `04-Quotes/`：只收可追溯的重要引文
- `05-Checks/`：章节很多时再拆出独立检查页

## 按书籍类型调整重心

- 非虚构：主张、论证、框架、定义、证据
- 小说/叙事：情节、人物、场景、母题、转折
- 传记/历史：时间线、行动者、因果链、解释框架

无论类型，都保持“章节优先，再做主题整合”。

## 链接与标签

标签统一用英文、小写、`kebab-case`，例如：

- `#book-...`
- `#theme-...`
- `#concept-...`
- `#character-...`
- `#note-chapter`
- `#note-theme`

链接规则：

1. `00-Overview/` 链到所有章节页和主题入口页
2. 每个章节页都要链接相关主题页或概念页
3. 主题页必须反链回章节页
4. 概念页要指出首次出现或主要出现章节
5. 引文页必须能回到章节页

## 可追溯性

始终区分：

- 原书直接信息
- 多章综合归纳
- 书外补充说明

规则：

1. 直接引文尽量附页码或章节锚点
2. 页码不稳定时明确说明
3. 综合归纳写清来源章节
4. 书外补充明确标成“补充说明”
5. 无法溯源的内容不要写成确定事实

## 语言

- 默认中文输出
- 保留原文术语、专有名词、关键引文
- 重要术语首次出现建议写成：`中文（Original Term）`
