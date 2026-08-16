# Bilibili Social Video Skill

[中文](#中文) · [English](#english)

## 中文

一个面向 AI Agent 的 B 站单视频下载 Skill。它使用 `yt-dlp`、`ffmpeg` 和 Python，把你有权使用的 B 站公开视频保存为适合剪映、Premiere Pro、Final Cut、抖音和小红书工作流的 MP4。

默认行为：免登录、最高 1080P、MP4、优先 H.264/AAC；只有原编码不兼容时才转码。

> 公开视频不等于无版权素材。请只下载和再利用你拥有权利或已获授权的内容。本项目不绕过 DRM、付费、私密或其他访问控制，也不提供去水印、批量搬运或自动发布功能。

### 安装依赖

```bash
# macOS
brew install yt-dlp ffmpeg

# Windows PowerShell
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg

# Linux：先用系统包管理器安装 ffmpeg，然后
python3 -m pip install --upgrade yt-dlp
```

### 使用

```bash
python3 skills/download-bilibili-video/scripts/bilibili_download.py doctor

python3 skills/download-bilibili-video/scripts/bilibili_download.py \
  inspect "https://www.bilibili.com/video/BV..."

python3 skills/download-bilibili-video/scripts/bilibili_download.py \
  download "https://www.bilibili.com/video/BV..." \
  --output-dir "./downloads" \
  --json
```

可选参数：

- `--max-height 1080`：最高分辨率。
- `--container mp4|mov`：默认 MP4，MOV 可选。
- `--mode compatible|original`：默认只在必要时转为 H.264/AAC。
- `--browser chrome|edge|firefox|safari`：仅在你明确选择时读取本机登录状态，不会导出 Cookie。

脚本只接受单个 `bilibili.com/video/...` 或 `b23.tv/...` 链接，会移除跟踪参数，并拒绝合集、播放列表和其他网站。

### 安装为 AI Agent Skill

把 [`skills/download-bilibili-video`](skills/download-bilibili-video) 复制到 Agent 支持的 skills 目录。支持 Agent Skills 的客户端可以直接读取 `SKILL.md`；不支持 Skill 安装、但能配置 Prompt 和本地工具的平台，可以把同一工作流作为系统提示词，并将 CLI 注册为 Function Tool。

豆包/火山引擎环境必须具备自定义 Skill、Shell 或 Function Tool 执行能力。普通聊天客户端如果不能运行本地命令，只能帮你生成命令，不能真的下载文件。

## English

An Agent Skill for downloading one Bilibili video that the user is authorized to reuse. It wraps `yt-dlp` and `ffmpeg` in a standard-library Python CLI and produces editing-friendly MP4 media for tools such as Jianying, Premiere Pro, and Final Cut.

Defaults: no login, up to 1080P, MP4, and H.264/AAC where available. The CLI transcodes only when the selected source codecs are not editing-friendly.

Public visibility does not grant reuse rights. Do not use this project to bypass DRM, payment, private access, or platform controls.

### Agent installation

Copy [`skills/download-bilibili-video`](skills/download-bilibili-video) into the skills directory supported by your Agent client. The Agent must be allowed to run Python, `yt-dlp`, `ffmpeg`, and `ffprobe`. Prompt-only chat clients can explain the command but cannot download the file.

See [`references/compatibility.md`](skills/download-bilibili-video/references/compatibility.md) for platform notes.

## License

MIT
