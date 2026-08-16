---
name: download-bilibili-video
description: Inspect and download one publicly accessible Bilibili video that the user is authorized to reuse, producing an editing-friendly H.264/AAC MP4 or optional MOV with yt-dlp and ffmpeg. Use when users ask to download or save a B站, Bilibili, BV, or b23.tv video for Douyin, Xiaohongshu, Jianying, Premiere Pro, or Final Cut editing, or when they need to inspect the selected video format first.
---

# Download Bilibili Video

Download one authorized Bilibili video with the bundled deterministic CLI. Default to a login-free, editing-friendly MP4 at up to 1080P.

## Safety boundary

- Confirm that the user has permission to download and reuse the video. Public visibility does not grant reuse rights.
- Do not bypass DRM, payment, private access, or platform controls.
- Do not request exported cookies or passwords. Use local browser cookies only when the user explicitly asks and already has lawful access.
- Do not treat this skill as a reposting, batch scraping, subtitle, watermark-removal, or publishing tool.

## Workflow

1. Locate `scripts/bilibili_download.py` relative to this `SKILL.md`.
2. Run `doctor` before the first use on a machine:

   ```bash
   python3 scripts/bilibili_download.py doctor
   ```

3. Inspect the single video before downloading:

   ```bash
   python3 scripts/bilibili_download.py inspect "BILIBILI_URL"
   ```

4. Download with defaults unless the user requests otherwise:

   ```bash
   python3 scripts/bilibili_download.py download "BILIBILI_URL" --output-dir "OUTPUT_DIR" --json
   ```

5. Report the absolute `output_path`, final resolution, codecs, whether browser cookies were used, and whether transcoding occurred. Do not claim success unless the command exits `0` and the output file exists.

## Options

- Default to `--max-height 1080 --container mp4 --mode compatible`.
- Use `--container mov` only when the user requests MOV.
- Use `--mode original` only when the user prefers the source codecs and accepts possible editor incompatibility.
- Add `--browser chrome|edge|firefox|safari` only after explicit user authorization. This reads the local signed-in browser session; it never exports cookies.
- Keep `--json` for agent-readable output.

Never reuse fixed Bilibili format IDs across videos. Let the CLI select formats dynamically.

## Failure handling

- Exit `2`: fix invalid input or install missing dependencies.
- Exit `3`: retry the network or yt-dlp step; update yt-dlp if Bilibili changed its site.
- Exit `4`: inspect ffmpeg availability and codec support.
- If no login-free 1080P format is available, explain the selected lower resolution. Offer local browser cookies only when the user explicitly wants to use their own login.

Read [references/compatibility.md](references/compatibility.md) for installation and Agent integration notes.
