---
name: skill-writer
description: 指导用户创建和管理新的 AI Skill，确保其符合标准结构和最佳实践。
---

# Skill Writer

这是一个专门用于辅助创建、更新和优化 AI Skill 的工具。

## 核心职责

1. **指导结构规范**：确保所有新创建的 Skill 都包含必要的 `SKILL.md`、`scripts/` 和 `examples/`（可选）目录。
2. **规范文件内容**：指导编写符合 YAML frontmatter 要求的 `SKILL.md`。
3. **自动化辅助**：提供脚本模板或建议，以增强 Skill 的功能。

## 目录结构要求

每个 Skill 必须遵循以下结构：

- `SKILL.md`: (必选) 包含名称、描述和详细指令的主文件。
- `scripts/`: (推荐) 包含辅助脚本或工具。
- `examples/`: (可选) 包含该 Skill 的使用示例。

## 如何编写 SKILL.md

`SKILL.md` 应当包含：

1. **YAML Frontmatter**:
   ```yaml
   ---
   name: skill-name
   description: brief description
   ---
   ```
2. **详细指令**: 解释该 Skill 的用途及具体操作步骤。
3. **工具使用指南**: 如果该 Skill 涉及特定的工具调用，请在此说明。

## 最佳实践

- **简洁明了**: 指令应易于理解和执行。
- **自包含**: Skill 应该尽可能减少对外部未说明依赖的需要。
- **可测试**: 尽量提供示例以便验证 Skill 的有效性。
