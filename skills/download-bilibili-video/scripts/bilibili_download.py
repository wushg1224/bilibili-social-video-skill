#!/usr/bin/env python3
"""Safely inspect and download one authorized Bilibili video."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit, urlunsplit


EXIT_INPUT = 2
EXIT_DOWNLOAD = 3
EXIT_POSTPROCESS = 4
SUPPORTED_BROWSERS = ("chrome", "edge", "firefox", "safari")
SUPPORTED_CONTAINERS = ("mp4", "mov")
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
BVID_PATTERN = re.compile(r"^BV[0-9A-Za-z]{10}$", re.IGNORECASE)
AVID_PATTERN = re.compile(r"^av[0-9]+$", re.IGNORECASE)


class CliError(Exception):
    def __init__(self, code: int, stage: str, message: str, hint: str) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message
        self.hint = hint


def empty_result(command: str) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "video_id": None,
        "title": None,
        "output_path": None,
        "height": None,
        "video_codec": None,
        "audio_codec": None,
        "container": None,
        "used_browser_cookies": False,
        "transcoded": False,
    }


def sanitize_message(message: str) -> str:
    home = str(Path.home())
    sanitized = message.replace(home, "<HOME>") if home else message
    sanitized = re.sub(r"(?i)(cookies?(?:\.txt)?\s*[:=]\s*)\S+", r"\1<redacted>", sanitized)
    return sanitized.strip()


def canonicalize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        raise CliError(EXIT_INPUT, "input", "The URL is empty.", "Provide one Bilibili video URL.")
    if "://" not in value:
        value = f"https://{value}"

    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in {"b23.tv", "www.b23.tv"}:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 1 or not re.fullmatch(r"[0-9A-Za-z_-]+", parts[0]):
            raise CliError(
                EXIT_INPUT,
                "input",
                "Only one b23.tv short-video link is supported.",
                "Provide a direct Bilibili video link, not a playlist or collection.",
            )
        return urlunsplit(("https", "b23.tv", f"/{parts[0]}", "", ""))

    allowed_hosts = {"bilibili.com", "www.bilibili.com", "m.bilibili.com"}
    if host not in allowed_hosts:
        raise CliError(
            EXIT_INPUT,
            "input",
            "Only bilibili.com and b23.tv video links are supported.",
            "Provide one direct Bilibili video URL.",
        )

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0].lower() != "video":
        raise CliError(
            EXIT_INPUT,
            "input",
            "Only a single Bilibili /video/ URL is supported.",
            "Collections, playlists, profiles, and search pages are outside this skill's scope.",
        )
    video_id = parts[1]
    if not (BVID_PATTERN.fullmatch(video_id) or AVID_PATTERN.fullmatch(video_id)):
        raise CliError(
            EXIT_INPUT,
            "input",
            "The Bilibili video ID is not valid.",
            "Use a URL containing a BV ID or av ID.",
        )
    if BVID_PATTERN.fullmatch(video_id):
        video_id = "BV" + video_id[2:]
    else:
        video_id = "av" + video_id[2:]
    return f"https://www.bilibili.com/video/{video_id}"


def format_selector(max_height: int) -> str:
    if max_height < 144 or max_height > 4320:
        raise CliError(
            EXIT_INPUT,
            "input",
            "--max-height must be between 144 and 4320.",
            "Use 1080 for the default social-editing workflow.",
        )
    height = str(max_height)
    return (
        f"bv*[height<={height}][vcodec^=avc1][ext=mp4]+"
        f"ba[acodec^=mp4a][ext=m4a]/"
        f"b[height<={height}][vcodec^=avc1][acodec^=mp4a][ext=mp4]/"
        f"bv*[height<={height}]+ba/b[height<={height}]"
    )


def cookie_args(browser: str | None) -> list[str]:
    return ["--cookies-from-browser", browser] if browser else []


def require_tool(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise CliError(
            EXIT_INPUT,
            "dependency",
            f"Required executable not found: {name}",
            "Install yt-dlp, ffmpeg, and ffprobe, then run doctor again.",
        )
    return resolved


def run_process(args: Sequence[str], code: int, stage: str, hint: str) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise CliError(code, stage, sanitize_message(str(exc)), hint) from exc
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or f"Command failed with exit code {completed.returncode}."
        raise CliError(code, stage, sanitize_message(detail), hint)
    return completed


def tool_version(name: str) -> str:
    executable = require_tool(name)
    args = [executable, "--version"] if name == "yt-dlp" else [executable, "-version"]
    completed = run_process(args, EXIT_INPUT, "dependency", f"Repair or reinstall {name}.")
    first_line = (completed.stdout or completed.stderr).splitlines()
    return first_line[0].strip() if first_line else "unknown"


def metadata_args(url: str, max_height: int, browser: str | None) -> list[str]:
    return [
        require_tool("yt-dlp"),
        "--simulate",
        "--no-playlist",
        "--no-warnings",
        "--dump-single-json",
        "-f",
        format_selector(max_height),
        *cookie_args(browser),
        url,
    ]


def fetch_metadata(url: str, max_height: int, browser: str | None) -> dict[str, Any]:
    completed = run_process(
        metadata_args(url, max_height, browser),
        EXIT_DOWNLOAD,
        "inspect",
        "Check the network, update yt-dlp, or explicitly choose a signed-in browser if authorized.",
    )
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CliError(
            EXIT_DOWNLOAD,
            "inspect",
            "yt-dlp returned metadata that was not valid JSON.",
            "Update yt-dlp and try again.",
        ) from exc
    if data.get("_type") in {"playlist", "multi_video"}:
        raise CliError(
            EXIT_INPUT,
            "input",
            "The link resolved to multiple videos.",
            "Provide one direct Bilibili video URL.",
        )
    return data


def selected_streams(metadata: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    requested = metadata.get("requested_formats") or []
    video = next((item for item in requested if item.get("vcodec") not in {None, "none"}), metadata)
    audio = next((item for item in requested if item.get("acodec") not in {None, "none"}), metadata)
    return video, audio


def metadata_result(metadata: dict[str, Any], browser: str | None) -> dict[str, Any]:
    video, audio = selected_streams(metadata)
    video_codec = video.get("vcodec") or metadata.get("vcodec")
    audio_codec = audio.get("acodec") or metadata.get("acodec")
    result = empty_result("inspect")
    result.update(
        {
            "video_id": metadata.get("id"),
            "title": metadata.get("title"),
            "height": video.get("height") or metadata.get("height"),
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "container": "mp4",
            "used_browser_cookies": bool(browser),
            "would_transcode": not codecs_are_compatible(video_codec, audio_codec),
        }
    )
    return result


def codecs_are_compatible(video_codec: str | None, audio_codec: str | None) -> bool:
    video_ok = bool(video_codec) and str(video_codec).lower().startswith(("h264", "avc1"))
    audio_ok = audio_codec in {None, "none"} or str(audio_codec).lower().startswith(("aac", "mp4a"))
    return video_ok and audio_ok


def find_downloaded_file(temp_dir: Path, output_marker: str) -> Path:
    if output_marker:
        candidate = Path(output_marker)
        if candidate.is_file():
            return candidate
    candidates = [path for path in temp_dir.iterdir() if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS]
    if len(candidates) == 1:
        return candidates[0]
    raise CliError(
        EXIT_DOWNLOAD,
        "download",
        "The downloaded media file could not be identified.",
        "Update yt-dlp and retry. Temporary files were not published.",
    )


def download_source(url: str, temp_dir: Path, max_height: int, browser: str | None) -> Path:
    template = str(temp_dir / "%(title).180B [%(id)s].%(ext)s")
    args = [
        require_tool("yt-dlp"),
        "--no-playlist",
        "--no-warnings",
        "--windows-filenames",
        "--trim-filenames",
        "200",
        "--merge-output-format",
        "mp4",
        "-f",
        format_selector(max_height),
        "-o",
        template,
        "--print",
        "after_move:__OUTPUT__%(filepath)s",
        *cookie_args(browser),
        url,
    ]
    completed = run_process(
        args,
        EXIT_DOWNLOAD,
        "download",
        "Check the network, update yt-dlp, or explicitly choose a signed-in browser if authorized.",
    )
    marker = ""
    for line in completed.stdout.splitlines():
        if line.startswith("__OUTPUT__"):
            marker = line.removeprefix("__OUTPUT__").strip()
    return find_downloaded_file(temp_dir, marker)


def probe_media(path: Path) -> dict[str, Any]:
    completed = run_process(
        [
            require_tool("ffprobe"),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        EXIT_POSTPROCESS,
        "probe",
        "Repair ffmpeg/ffprobe and retry.",
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CliError(
            EXIT_POSTPROCESS,
            "probe",
            "ffprobe returned invalid JSON.",
            "Repair ffmpeg/ffprobe and retry.",
        ) from exc


def probe_summary(probe: dict[str, Any]) -> tuple[int | None, str | None, str | None]:
    streams = probe.get("streams") or []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    return video.get("height"), video.get("codec_name"), audio.get("codec_name")


def unique_destination(output_dir: Path, stem: str, container: str) -> Path:
    candidate = output_dir / f"{stem}.{container}"
    index = 1
    while candidate.exists():
        candidate = output_dir / f"{stem} ({index}).{container}"
        index += 1
    return candidate


def finalize_media(source: Path, output_dir: Path, container: str, mode: str) -> tuple[Path, bool]:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = unique_destination(output_dir, source.stem, container)
    source_probe = probe_media(source)
    _, video_codec, audio_codec = probe_summary(source_probe)
    compatible = codecs_are_compatible(video_codec, audio_codec)
    needs_transcode = mode == "compatible" and not compatible
    same_container = source.suffix.lower() == f".{container}"

    if not needs_transcode and same_container:
        shutil.move(str(source), str(destination))
        return destination.resolve(), False

    ffmpeg_args = [
        require_tool("ffmpeg"),
        "-v",
        "error",
        "-n",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    if needs_transcode:
        ffmpeg_args.extend(
            [
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ]
        )
    else:
        ffmpeg_args.extend(["-c", "copy"])
    ffmpeg_args.extend(["-movflags", "+faststart", str(destination)])
    try:
        run_process(
            ffmpeg_args,
            EXIT_POSTPROCESS,
            "postprocess",
            "Confirm that ffmpeg includes H.264/AAC support and that the output directory is writable.",
        )
    except CliError:
        destination.unlink(missing_ok=True)
        raise
    return destination.resolve(), needs_transcode


def doctor_result() -> dict[str, Any]:
    result = empty_result("doctor")
    result["dependencies"] = {
        "python": sys.version.split()[0],
        "yt-dlp": tool_version("yt-dlp"),
        "ffmpeg": tool_version("ffmpeg"),
        "ffprobe": tool_version("ffprobe"),
    }
    return result


def inspect_result(url: str, browser: str | None) -> dict[str, Any]:
    canonical = canonicalize_url(url)
    metadata = fetch_metadata(canonical, 1080, browser)
    return metadata_result(metadata, browser)


def download_result(args: argparse.Namespace) -> dict[str, Any]:
    canonical = canonicalize_url(args.url)
    require_tool("ffmpeg")
    require_tool("ffprobe")
    metadata = fetch_metadata(canonical, args.max_height, args.browser)
    initial = metadata_result(metadata, args.browser)
    output_dir = Path(args.output_dir).expanduser().resolve()

    with tempfile.TemporaryDirectory(prefix="bilibili-download-") as temp_name:
        source = download_source(canonical, Path(temp_name), args.max_height, args.browser)
        destination, transcoded = finalize_media(source, output_dir, args.container, args.mode)

    try:
        final_probe = probe_media(destination)
    except CliError:
        destination.unlink(missing_ok=True)
        raise
    height, video_codec, audio_codec = probe_summary(final_probe)
    result = empty_result("download")
    result.update(
        {
            "video_id": initial["video_id"],
            "title": initial["title"],
            "output_path": str(destination),
            "height": height,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "container": args.container,
            "used_browser_cookies": bool(args.browser),
            "transcoded": transcoded,
        }
    )
    return result


def emit_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return
    command = result["command"]
    if command == "doctor":
        print("Ready")
        for name, version in result["dependencies"].items():
            print(f"{name}: {version}")
    elif command == "inspect":
        print(f"Title: {result['title']}")
        print(f"Video ID: {result['video_id']}")
        print(f"Selected: {result['height']}p, {result['video_codec']} + {result['audio_codec']}, MP4")
        print(f"Would transcode: {'yes' if result.get('would_transcode') else 'no'}")
        print(f"Browser cookies: {'yes' if result['used_browser_cookies'] else 'no'}")
    else:
        print(f"Saved: {result['output_path']}")
        print(f"Final: {result['height']}p, {result['video_codec']} + {result['audio_codec']}, {result['container']}")
        print(f"Transcoded: {'yes' if result['transcoded'] else 'no'}")
        print(f"Browser cookies: {'yes' if result['used_browser_cookies'] else 'no'}")


def emit_error(error: CliError, as_json: bool) -> None:
    payload = {
        "ok": False,
        "stage": error.stage,
        "message": sanitize_message(error.message),
        "hint": sanitize_message(error.hint),
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Error [{error.stage}]: {payload['message']}", file=sys.stderr)
        print(f"Hint: {payload['hint']}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or download one authorized Bilibili video for editing.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local dependencies.")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect the selected format without downloading.")
    inspect_parser.add_argument("url")
    inspect_parser.add_argument("--browser", choices=SUPPORTED_BROWSERS)
    inspect_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    download = subparsers.add_parser("download", help="Download one video.")
    download.add_argument("url")
    download.add_argument("--output-dir", default=".")
    download.add_argument("--max-height", type=int, default=1080)
    download.add_argument("--container", choices=SUPPORTED_CONTAINERS, default="mp4")
    download.add_argument("--mode", choices=("compatible", "original"), default="compatible")
    download.add_argument("--browser", choices=SUPPORTED_BROWSERS)
    download.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    as_json = bool(args.json)
    try:
        if args.command == "doctor":
            result = doctor_result()
        elif args.command == "inspect":
            result = inspect_result(args.url, args.browser)
        else:
            print("Only download content you are authorized to use.", file=sys.stderr)
            result = download_result(args)
        emit_result(result, as_json)
        return 0
    except CliError as error:
        emit_error(error, as_json)
        return error.code


if __name__ == "__main__":
    raise SystemExit(main())
