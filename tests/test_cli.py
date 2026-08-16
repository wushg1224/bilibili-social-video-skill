from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "download-bilibili-video" / "scripts" / "bilibili_download.py"
SPEC = importlib.util.spec_from_file_location("bilibili_download", SCRIPT)
assert SPEC and SPEC.loader
bd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bd)


class UrlTests(unittest.TestCase):
    def test_canonicalizes_and_removes_tracking_parameters(self) -> None:
        raw = (
            "https://www.bilibili.com/video/BV1Ab411CdEf"
            "?spm_id_from=333.788&trackid=value&vd_source=value"
        )
        self.assertEqual(
            bd.canonicalize_url(raw),
            "https://www.bilibili.com/video/BV1Ab411CdEf",
        )

    def test_accepts_short_link_without_query(self) -> None:
        self.assertEqual(bd.canonicalize_url("https://b23.tv/AbC123?x=1"), "https://b23.tv/AbC123")

    def test_rejects_non_bilibili_domain(self) -> None:
        with self.assertRaises(bd.CliError) as raised:
            bd.canonicalize_url("https://example.com/video/BV1Ab411CdEf")
        self.assertEqual(raised.exception.code, 2)

    def test_rejects_playlist_path(self) -> None:
        with self.assertRaises(bd.CliError):
            bd.canonicalize_url("https://www.bilibili.com/list/123")


class SelectionTests(unittest.TestCase):
    def test_selector_is_dynamic_and_height_limited(self) -> None:
        selector = bd.format_selector(1080)
        self.assertIn("height<=1080", selector)
        self.assertIn("vcodec^=avc1", selector)
        self.assertNotIn("30112", selector)

    def test_cookie_flag_is_opt_in(self) -> None:
        self.assertEqual(bd.cookie_args(None), [])
        self.assertEqual(bd.cookie_args("chrome"), ["--cookies-from-browser", "chrome"])

    def test_codec_compatibility(self) -> None:
        self.assertTrue(bd.codecs_are_compatible("avc1.640032", "mp4a.40.2"))
        self.assertTrue(bd.codecs_are_compatible("h264", "aac"))
        self.assertFalse(bd.codecs_are_compatible("av1", "aac"))
        self.assertFalse(bd.codecs_are_compatible("h264", "opus"))

    @mock.patch.object(bd, "require_tool", return_value="yt-dlp")
    def test_metadata_command_disables_playlists(self, _mocked: mock.Mock) -> None:
        args = bd.metadata_args("https://www.bilibili.com/video/BV1Ab411CdEf", 1080, None)
        self.assertIn("--no-playlist", args)
        self.assertNotIn("--cookies-from-browser", args)


class OutputTests(unittest.TestCase):
    def test_empty_result_has_stable_agent_fields(self) -> None:
        expected = {
            "ok",
            "command",
            "video_id",
            "title",
            "output_path",
            "height",
            "video_codec",
            "audio_codec",
            "container",
            "used_browser_cookies",
            "transcoded",
        }
        self.assertTrue(expected.issubset(bd.empty_result("doctor")))

    def test_sanitizes_home_path(self) -> None:
        self.assertNotIn(str(Path.home()), bd.sanitize_message(f"failed at {Path.home()}/cookies.sqlite"))

    def test_invalid_url_json_exit_code(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "inspect", "https://example.com/video/123", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["stage"], "input")

    def test_unique_destination_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            directory = Path(temp_name)
            (directory / "video.mp4").touch()
            self.assertEqual(bd.unique_destination(directory, "video", "mp4").name, "video (1).mp4")


if __name__ == "__main__":
    unittest.main()
