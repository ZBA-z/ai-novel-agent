# ai-novel-agent

AI 长篇小说（网文）写作智能体 Skill：三人格协作流水线（选品 Scout / 写作 Author / 评审 Reader）＋跨会话状态块＋闸门质检＋去 AI 味规则台账＋AI 生成内容声明合规。

平台中立：包内为纯 Markdown ＋ 一个 Python 自检脚本，不依赖任何专有工具的 API。

## 安装

### 方式 A：WorkBuddy / CodeBuddy（最简）

在对话里给出本仓库链接，让技能安装器完成：

```
https://github.com/ZBA-z/ai-novel-agent
```

### 方式 B：手动解压

1. 下载 [`dist/ai-novel-agent.skill`](dist/ai-novel-agent.skill)（或仓库 zip：Code → Download ZIP）
2. 解压到用户级技能目录：
   - Windows：`C:\Users\<用户名>\.workbuddy\skills\ai-novel-agent\`
   - macOS / Linux：`~/.workbuddy/skills/ai-novel-agent/`
3. 确认 `SKILL.md` 位于 `ai-novel-agent\` 根下，重启会话即被识别

### 方式 C：任意其他 AI 工具 / 纯对话

解压到对应工具的 skills 目录（如 `~/.claude/skills/ai-novel-agent/`）；
或把 `20_人格\` 下三张人格卡当系统提示词粘贴到任意聊天工具，配合 `10_内核\02_状态规格.md` 的状态块手动携带即可跑通「细纲 → 正文 → 评审」。

## 目录结构

```
SKILL.md            ← 技能入口：工作流路由＋硬约束
10_内核/            ← 状态、闸门、交接物、目录模板、日志、AI 声明（系统的"法律"）
20_人格/            ← Scout / Author / Reader 三张人格卡
30_台账/            ← 去 AI 味规则台账（空表＋规格）
tools/check-bundle.py  ← 交付集自洽校验器
dist/               ← 打包好的 .skill 安装文件
```

## 触发语

「帮我写小说」「搭一个 AI 写网文的流程」「写细纲 / 写正文」「评审这一章」「去 AI 味」等。

## 使用者需知

1. **去 AI 味台账是空表**：安装后该维度为 0，空台账报警是预期行为，需自行提供正负对照语料填充
2. **风格库不在包内**：文风锚为空，需自备参考文风（模板见 `10_内核\07_角色卡与状态快照模板.md`）
3. 修改本包文件后，在包根目录运行 `python tools/check-bundle.py`，退出码 0 才算改完

## 版本

- **v1.0.0**（2026-09-19）：首个公开版本。内核 8 ＋ 人格 4 ＋ 台账 2 ＋ 自检脚本，经 4 轮独立审计修正。

## 许可

仅供学习与个人创作使用。
