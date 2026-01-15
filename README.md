# My Skills Writer

这是一个用于存放和管理自定义 AI Skill 的项目。通过这些 Skill，可以增强 AI 助手的自动化能力，例如规范化 Skill 编写流程或自动化下载任务。

## 已包含的 Skill

### 1. [Skill Writer](./skill-writer/SKILL.md)
专门用于辅助创建、更新和优化 AI Skill 的工具。它定义了本项目中 Skill 的标准目录结构和编写规范。

### 2. [Video Downloader](./video-downloader/SKILL.md)
自动化视频下载工具，基于 `nre` (N_m3u8DL-RE) 命令。
- **功能**: 自动从用户提供的链接中提取视频并以指定名称保存。
- **依赖**: 需要安装 [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE)。

## 目录结构

```text
.
├── README.md
├── skill-writer/        # Skill 编写规范
│   └── SKILL.md
└── video-downloader/    # 视频下载工具
    ├── SKILL.md
    └── scripts/
        └── download.sh
```

## 如何贡献

如果你想添加新的 Skill，请参考 `skill-writer` 中的规范进行创建，并将其放置在独立的文件夹中。
