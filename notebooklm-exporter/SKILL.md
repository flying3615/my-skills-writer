---
name: notebooklm-exporter
description: Use when you need to manage NotebookLM notebooks, sources, artifacts, generation, and downloads through the notebooklm CLI.
---

# NotebookLM Exporter Skill

这个 Skill 用于把 `notebooklm` CLI 封装成一组稳定的常用工作流，方便 AI 助手直接完成 NotebookLM 的检查、查看、生成、导出和 source 管理操作。

## 适用场景

- 检查 `notebooklm-py` 是否安装并已登录
- 列出 notebook、source、artifact
- 查看 notebook 摘要、metadata、source guide、source fulltext
- 向 notebook 添加 URL、文件、文本、research source
- 生成 `audio`、`video`、`infographic`、`report`、`quiz`、`flashcards`、`mind-map`、`data-table`、`slide-deck`
- 下载或导出 NotebookLM 已生成的 artifact

## 依赖

- 本机已安装 `notebooklm-py`
- 已完成一次 `notebooklm login`
- 推荐始终使用完整 `notebook ID`，不要依赖长标题；部分 shared notebook 对 UUID 前缀支持不稳定

首次安装通常需要：

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
notebooklm login
```

## 核心脚本

### 1. 检查环境

```bash
bash notebooklm-exporter/scripts/check_ready.sh
```

### 2. 查看 notebook 信息

```bash
bash notebooklm-exporter/scripts/notebook_ops.sh list
bash notebooklm-exporter/scripts/notebook_ops.sh summary --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --topics
bash notebooklm-exporter/scripts/notebook_ops.sh metadata --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --json
```

### 3. 管理 sources

```bash
bash notebooklm-exporter/scripts/source_ops.sh list --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937
bash notebooklm-exporter/scripts/source_ops.sh get --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --source 14c2a1fd
bash notebooklm-exporter/scripts/source_ops.sh guide --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --source 14c2a1fd
bash notebooklm-exporter/scripts/source_ops.sh fulltext --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --source 14c2a1fd --output ./fulltext.txt
bash notebooklm-exporter/scripts/source_ops.sh add --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --content "https://example.com"
bash notebooklm-exporter/scripts/source_ops.sh research --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --query "life philosophy" --mode deep --import-all
```

### 4. 管理 artifacts

```bash
bash notebooklm-exporter/scripts/artifact_ops.sh list --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --type video
bash notebooklm-exporter/scripts/artifact_ops.sh get --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --artifact 4d7fbd41
bash notebooklm-exporter/scripts/artifact_ops.sh suggestions --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937
bash notebooklm-exporter/scripts/artifact_ops.sh export --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --artifact 4d7fbd41 --title "NotebookLM Export" --export-type docs
```

### 5. 生成并下载 artifact

```bash
bash notebooklm-exporter/scripts/generate_and_download.sh \
  --artifact video \
  --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 \
  --description "make it concise" \
  --output ./out/video.mp4
```

### 6. 下载已有 artifact

```bash
bash notebooklm-exporter/scripts/download_artifact.sh \
  --artifact video \
  --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 \
  --artifact-id 4d7fbd41 \
  --output ./out/video.mp4
```

批量下载常见媒体：

```bash
bash notebooklm-exporter/scripts/download_artifact.sh \
  --all-media \
  --notebook 750a23df \
  --output-dir ./out
```

## 注意事项

- 这个 Skill 只是 NotebookLM 的包装层，不会绕过 NotebookLM 登录
- wrapper 脚本优先走 `-n <full-notebook-id>`，避免 `notebooklm use "<title>"` 在 shared notebook 上不稳定
- 如果需要 NotebookLM 原生命令的完整能力，可以直接调用 `notebooklm ...`
