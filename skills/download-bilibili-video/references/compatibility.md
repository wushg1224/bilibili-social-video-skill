# Compatibility and installation

## Runtime requirements

- Python 3.10 or newer
- A recent `yt-dlp` executable on `PATH`
- `ffmpeg` and `ffprobe` on `PATH`
- Network access to Bilibili

Typical installation commands:

```bash
# macOS
brew install yt-dlp ffmpeg

# Windows (PowerShell)
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg

# Linux: install ffmpeg with the distribution package manager, then
python3 -m pip install --upgrade yt-dlp
```

Run `python3 scripts/bilibili_download.py doctor --json` after installation.

## Agent Skills clients

Install the `download-bilibili-video` folder in the skills directory supported by the client. Common locations include project-level `.agents/skills/`, Codex personal skills, and Claude Code skills. Consult the current client documentation for its exact discovery path.

The skill needs permission to execute Python and the listed local binaries. An Agent that can read instructions but cannot run local tools can only produce a command for the user to run.

## Doubao and Volcengine agents

When the Agent environment supports custom Skills, import the skill folder. When it supports only prompts and Function Tools, use the safety boundary and workflow from `SKILL.md` as the system instructions, then expose this CLI as an approved local tool.

Do not claim that the ordinary Doubao chat client downloaded a file when it has no shell, sandbox, or Function Tool capable of running the CLI.

## Browser cookies

Cookie access is opt-in through `--browser`. Supported values are `chrome`, `edge`, `firefox`, and `safari`; Safari is macOS-only. The CLI passes only the browser name to yt-dlp and sanitizes user-home paths from surfaced errors. Never upload or commit browser profiles or exported cookie files.
