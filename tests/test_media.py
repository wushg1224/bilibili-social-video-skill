from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "download-bilibili-video" / "scripts" / "bilibili_download.py"
SPEC = importlib.util.spec_from_file_location("bilibili_download_media", SCRIPT)
assert SPEC and SPEC.loader
bd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bd)


def has_libx264() -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        check=False,
        capture_output=True,
        text=True,
    )
    return "libx264" in completed.stdout


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe") and has_libx264(), "ffmpeg with libx264 required")
class MediaTests(unittest.TestCase):
    def make_media(self, path: Path, video_codec: str) -> None:
        subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=25",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:sample_rate=44100",
                "-t",
                "0.5",
                "-c:v",
                video_codec,
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(path),
            ],
            check=True,
        )

    def test_compatible_media_moves_without_transcoding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source.mp4"
            output = root / "output"
            self.make_media(source, "libx264")
            destination, transcoded = bd.finalize_media(source, output, "mp4", "compatible")
            self.assertFalse(transcoded)
            self.assertTrue(destination.is_file())
            _, video_codec, audio_codec = bd.probe_summary(bd.probe_media(destination))
            self.assertEqual(video_codec, "h264")
            self.assertEqual(audio_codec, "aac")

    def test_incompatible_media_is_transcoded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source.mp4"
            output = root / "output"
            self.make_media(source, "mpeg4")
            destination, transcoded = bd.finalize_media(source, output, "mp4", "compatible")
            self.assertTrue(transcoded)
            _, video_codec, audio_codec = bd.probe_summary(bd.probe_media(destination))
            self.assertEqual(video_codec, "h264")
            self.assertEqual(audio_codec, "aac")


if __name__ == "__main__":
    unittest.main()
