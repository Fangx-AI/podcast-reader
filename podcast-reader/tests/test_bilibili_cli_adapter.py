"""Offline coverage for the explicitly selected anonymous bili-cli adapter."""

import asyncio
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ingest_bilibili_cli as adapter

BVID = "BV1tQYN6UE57"
STREAM = "https://cdn.example.com/audio.m4s?token=NEVER_PERSIST&signature=SIGNED_SECRET"


class FakeClient:
    def __init__(self, pages=None):
        self.calls = []
        self.info = {"bvid": BVID, "title": "Original title", "desc": "Public description",
                     "duration": 90000, "pubdate": 1704067200, "owner": {"name": "Publisher"},
                     "pages": pages or [{"page": 1, "cid": 101, "part": "Part one", "duration": 60}],
                     "hidden_play_context": {"url": STREAM}}

    async def get_video_info(self, bvid, *, credential):
        self.calls.append(("metadata", bvid, credential))
        print(STREAM)  # Third-party logging must not escape into stdout.
        return copy.deepcopy(self.info)

    async def get_audio_url(self, bvid, *, credential):
        self.calls.append(("audio", bvid, credential))
        print(STREAM)
        return STREAM


class BilibiliCliAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bili-cli-adapter-test-")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def run_adapter(self, client, value=BVID, **kwargs):
        def download(url, destination, referer, **bounds):
            self.assertEqual(url, STREAM)
            self.assertEqual(bounds["max_bytes"], kwargs.get("max_bytes", adapter.MAX_BYTES))
            destination.write_bytes(b"downloaded-media")
            return {"size_bytes": 16, "expected_size_bytes": 16}

        def convert(args, cwd):
            self.assertIn("0:a:0", args)
            self.assertEqual(args[args.index("-c:a") + 1], "copy")
            Path(args[-1]).write_bytes(b"audio-only")
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch.object(adapter, "command", return_value="installed"), \
                patch.object(adapter, "media_duration", return_value=60), \
                patch.object(adapter, "download_public_stream", side_effect=download) as downloader, \
                patch.object(adapter, "run", side_effect=convert), \
                patch.object(sys, "stdout", new_callable=io.StringIO) as stdout:
            result = asyncio.run(adapter.acquire(value, self.folder, client=client, **kwargs))
            self.assertNotIn("NEVER_PERSIST", stdout.getvalue())
            return result, downloader.call_count

    def test_single_part_is_anonymous_bounded_and_prepare_compatible(self):
        client = FakeClient()
        result, downloads = self.run_adapter(client, f"https://www.bilibili.com/video/{BVID}/?p=1&token=PRIVATE", max_duration_minutes=1)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["transcript_status"], "needs_transcription")
        self.assertEqual(downloads, 1)
        self.assertEqual(client.calls, [("metadata", BVID, None), ("audio", BVID, None)])
        self.assertEqual(result["source"]["duration_seconds"], 60)
        self.assertEqual(result["source"]["cookie_mode"], "none")
        self.assertEqual(result["source"]["kind"], "remote_media")
        self.assertEqual(result["source"]["published"], "20240101")
        self.assertEqual(result["files"]["audio"], result["files"]["media"])
        self.assertTrue(Path(result["files"]["audio"][0]).is_file())
        for path in self.folder.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            for secret in ("NEVER_PERSIST", "SIGNED_SECRET", "PRIVATE", "cdn.example.com"):
                self.assertNotIn(secret, text)
        # The normal local transcript attachment path retains adapter provenance
        # and finds its audio without changing prepare_episode's default route.
        prepared = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "prepare_episode.py"),
            result["source"]["canonical_url"], "--output-dir", str(self.folder),
            "--transcript", str(ROOT / "tests" / "fixtures" / "sample.srt"),
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(prepared.returncode, 0, prepared.stderr or prepared.stdout)
        bundle = json.loads(prepared.stdout)
        self.assertEqual(bundle["status"], "ready_for_analysis")
        self.assertIn(Path(result["files"]["audio"][0]).name, bundle["artifacts"]["media"])
        source = json.loads((self.folder / "source.json").read_text(encoding="utf-8"))
        self.assertEqual(source["ingestion_adapter"], "bili-cli:anonymous")
        self.assertEqual(source["kind"], "remote_media")
        self.assertEqual(source["published"], "20240101")

    def test_invalid_publication_dates_remain_unknown(self):
        for value in (None, "not a date", True, -1, float("nan"), 1e100):
            with self.subTest(value=value):
                self.assertIsNone(adapter.published_date(value))

    def test_multi_part_requires_selection_without_download(self):
        client = FakeClient([{"page": 1, "cid": 101, "duration": 60}, {"page": 2, "cid": 202, "duration": 120}])
        result, downloads = self.run_adapter(client)
        self.assertEqual(result["status"], "needs_selection")
        self.assertEqual(downloads, 0)
        self.assertEqual(len(result["available_parts"]), 2)
        self.assertEqual(len(client.calls), 1)

    def test_selected_second_part_uses_its_cid_not_first_part(self):
        client = FakeClient([{"page": 1, "cid": 101, "duration": 90000}, {"page": 2, "cid": 202, "duration": 60}])
        sdk_calls = []

        class Video:
            def __init__(self, *, bvid, credential):
                sdk_calls.append((bvid, credential))

            async def get_download_url(self, *, cid):
                sdk_calls.append(cid)
                return {"data": "private runtime data"}

        class Detector:
            def __init__(self, data):
                pass

            def detect_best_streams(self, **kwargs):
                return [None, SimpleNamespace(audio_quality=1, url=STREAM)]

            def check_flv_mp4_stream(self):
                return False

        sdk = SimpleNamespace(Video=Video, VideoDownloadURLDataDetecter=Detector, AudioQuality=SimpleNamespace(_64K=1))
        with patch.object(adapter.importlib, "import_module", return_value=sdk):
            result, downloads = self.run_adapter(client, f"https://www.bilibili.com/video/{BVID}/?p=2", max_duration_minutes=1)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(sdk_calls, [(BVID, None), 202])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(downloads, 1)
        self.assertEqual(result["source"]["selected_part"]["page"], 2)
        self.assertIn("?p=2", result["source"]["canonical_url"])

    def test_metadata_never_downloads_audio(self):
        result, downloads = self.run_adapter(FakeClient(), mode="metadata")
        self.assertEqual(result["status"], "metadata_only")
        self.assertEqual(downloads, 0)

    def test_limit_unknown_duration_and_invalid_selections_stop_before_audio(self):
        for kwargs in ({"max_duration_minutes": 0.5}, {"page": 2}, {"max_duration_minutes": float("nan")}):
            with self.subTest(kwargs=kwargs):
                client = FakeClient()
                result, downloads = self.run_adapter(client, **kwargs)
                self.assertIn(result["status"], {"blocked", "partial"})
                self.assertEqual(downloads, 0)
                self.assertFalse(any(call[0] == "audio" for call in client.calls))
        client = FakeClient()
        client.info["pages"][0]["duration"] = None
        client.info["duration"] = None
        result, downloads = self.run_adapter(client, max_duration_minutes=0)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(downloads, 0)

    def test_conflicting_or_unsafe_inputs_are_rejected(self):
        for value, page in ((f"https://www.bilibili.com/video/{BVID}/?p=2", 1),
                            (f"https://attacker.example/video/{BVID}/", None),
                            (f"https://user:pass@www.bilibili.com/video/{BVID}/", None),
                            (f"https://www.bilibili.com/video/{BVID}/?p=0", None),
                            (f"https://www.bilibili.com/video/{BVID}/?p=1&p=2", None)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                adapter.parse_source(value, page)

    def test_missing_backend_does_not_install_or_acquire(self):
        with patch.object(adapter.importlib, "import_module", side_effect=ModuleNotFoundError), \
                patch.object(adapter, "run") as runner:
            result = asyncio.run(adapter.acquire(BVID, self.folder))
        self.assertEqual(result["status"], "blocked")
        self.assertIn("Nothing was installed", result["warnings"][0]["message"])
        runner.assert_not_called()

    def test_failed_download_cleans_temporary_files_and_redacts_url(self):
        with patch.object(adapter, "command", return_value="installed"), \
                patch.object(adapter, "download_public_stream", side_effect=RuntimeError(f"failed {STREAM}")):
            result = asyncio.run(adapter.acquire(BVID, self.folder, client=FakeClient()))
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["files"]["media"])
        self.assertFalse(list(self.folder.glob(".bili-cli-*")))
        self.assertNotIn("SIGNED_SECRET", json.dumps(result))
        self.assertNotIn("cdn.example.com", (self.folder / "ingest-result.json").read_text())

    def test_incomplete_audio_is_not_published_and_valid_cache_is_reused(self):
        result, downloads = self.run_adapter(FakeClient())
        path = Path(result["files"]["audio"][0])
        again, downloads = self.run_adapter(FakeClient())
        self.assertEqual(again["cache"], "reused")
        self.assertEqual(downloads, 0)
        original = path.read_bytes()
        with patch.object(adapter, "command", return_value="installed"), \
                patch.object(adapter, "download_public_stream", side_effect=lambda _url, target, _ref, **_kw: target.write_bytes(b"short")), \
                patch.object(adapter, "media_duration", return_value=5):
            failed = asyncio.run(adapter.acquire(BVID, self.folder, client=FakeClient(), force=True))
        self.assertEqual(failed["status"], "partial")
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(failed["files"]["media"])
        self.assertFalse(list(self.folder.glob(".bili-cli-*")))


if __name__ == "__main__":
    unittest.main()
