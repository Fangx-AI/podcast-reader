import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from resolve_podcast import parse_rss
from ingest_media import bilibili_public_metadata, classify_files, compact_metadata, write_bilibili_audio
from combine_chunk_transcripts import combine
from prepare_audio_chunks import split_audio
from transcribe_local import transcribe_one
from validate_bundle import validate as validate_bundle
from validate_notes import validate as validate_notes


class MediaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/html"):
            body, media_type = b"<html>not media</html>", "text/html"
        else:
            body, media_type = (b"ID3" + self.path.encode("ascii") * 20), "audio/mpeg"
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


class ProductScenarioTests(unittest.TestCase):
    def invoke(self, name, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, msg=result.stderr or result.stdout)
        stream = result.stdout if result.stdout.strip() else result.stderr
        return json.loads(stream)

    def test_latest_feed_uses_date_not_document_order(self):
        feed = b"""<rss><channel><title>x</title>
        <item><title>Old</title><guid>old</guid><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
        <item><title>New</title><guid>new</guid><pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate></item>
        </channel></rss>"""
        result = parse_rss(feed, "https://example.com/feed.xml", latest=True)
        self.assertEqual(result["episode"]["guid"], "new")

    def test_metadata_mode_never_downloads_rss_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "episode"
            result = self.invoke("prepare_episode.py", FIXTURES / "sample.rss", "--query", "第一期：证据与产品", "--mode", "metadata", "--output-dir", output)
            self.assertEqual(result["status"], "metadata_only")
            self.assertEqual(result["artifacts"]["media"], [])

    def test_subtitles_mode_does_not_fall_back_to_rss_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "episode"
            result = self.invoke("prepare_episode.py", FIXTURES / "sample.rss", "--query", "第二期：系统设计", "--mode", "subtitles", "--output-dir", output)
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["artifacts"]["media"], [])

    def test_metadata_cache_does_not_block_later_subtitles_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "episode"
            first = self.invoke("prepare_episode.py", FIXTURES / "sample.rss", "--query", "第二期：系统设计", "--mode", "metadata", "--output-dir", output)
            self.assertEqual(first["status"], "metadata_only")
            second = self.invoke("prepare_episode.py", FIXTURES / "sample.rss", "--query", "第二期：系统设计", "--mode", "subtitles", "--output-dir", output)
            self.assertNotIn("cache", second)
            self.assertEqual(second["request"]["mode"], "subtitles")

    def test_direct_media_metadata_mode_does_not_download(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "episode"
            result = self.invoke("prepare_episode.py", "https://cdn.example.com/episode.mp3", "--mode", "metadata", "--output-dir", output)
            self.assertEqual(result["status"], "metadata_only")
            self.assertTrue((output / "source.json").is_file())
            self.assertEqual(result["artifacts"]["media"], [])

    def test_signed_media_parameters_are_not_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "episode"
            result = self.invoke("prepare_episode.py", "https://cdn.example.com/episode.mp3?token=secret&expires=999", "--mode", "metadata", "--output-dir", output)
            serialized = json.dumps(result, ensure_ascii=False)
            source_text = (output / "source.json").read_text(encoding="utf-8")
            self.assertNotIn("secret", serialized)
            self.assertNotIn("token=", source_text)

    def test_generated_transcript_can_resume_existing_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root / "episode.mp3"
            media.write_bytes(b"ID3fake")
            output = root / "bundle"
            first = self.invoke("prepare_episode.py", media, "--output-dir", output)
            self.assertEqual(first["status"], "needs_transcription")
            resumed = self.invoke("prepare_episode.py", media, "--output-dir", output, "--transcript", FIXTURES / "sample.srt")
            self.assertEqual(resumed["status"], "ready_for_analysis")
            self.assertTrue((output / "transcript-raw.srt").is_file())
            self.assertTrue(validate_bundle(output)["valid"])

    def test_huge_plain_transcript_is_really_chunked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            transcript = root / "long.txt"
            transcript.write_text("这是一个很长的无时间戳段落。" * 1000, encoding="utf-8")
            normalized = self.invoke("normalize_transcript.py", transcript, "--output-dir", root)
            self.assertEqual(normalized["segment_count"], 1)
            self.invoke("chunk_transcript.py", root / "transcript.json", "-o", root / "chunks.json", "--max-chars", "500", "--overlap-segments", "0")
            chunks = json.loads((root / "chunks.json").read_text(encoding="utf-8"))["chunks"]
            self.assertGreater(len(chunks), 10)
            self.assertTrue(all(chunk["char_count"] <= 500 for chunk in chunks))

    def test_bundle_validator_requires_source_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bundle.json").write_text(json.dumps({"schema_version": "1.0", "bundle_id": "x", "source_input": "x", "status": "partial", "next_actions": ["x"], "artifacts": {}}), encoding="utf-8")
            result = validate_bundle(root)
            self.assertFalse(result["valid"])
            self.assertIn("source.json is missing", result["errors"])

    def test_report_url_does_not_substitute_for_source_field(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "report.md"
            report.write_text("# Report\n\nSee https://example.com.\n\n## Summary\nText.\n", encoding="utf-8")
            self.assertFalse(validate_notes(report)["valid"])

    def test_direct_downloader_rejects_html_and_avoids_name_collisions(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), MediaHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                base = f"http://127.0.0.1:{server.server_port}"
                blocked = self.invoke("fetch_audio.py", f"{base}/html/default.mp3", "--output-dir", folder, "--allow-private-network", expected=1)
                self.assertEqual(blocked["stage"], "download")
                first = self.invoke("fetch_audio.py", f"{base}/one/default.mp3", "--output-dir", folder, "--allow-private-network")
                second = self.invoke("fetch_audio.py", f"{base}/two/default.mp3", "--output-dir", folder, "--allow-private-network")
                self.assertNotEqual(first["path"], second["path"])
        finally:
            server.shutdown()
            server.server_close()

    def test_default_youtube_folder_contains_video_id(self):
        from prepare_episode import derive_episode_dir, source_key
        result = derive_episode_dir(Path("outputs"), "https://www.youtube.com/watch?v=abc123", {"kind": "youtube"})
        self.assertIn("abc123", result.name)
        self.assertEqual(source_key("https://youtube.com/watch?v=abc123&t=90&si=x"), source_key("https://youtube.com/watch?v=abc123"))

    def test_bilibili_private_play_context_is_not_persisted(self):
        compact = compact_metadata({
            "id": "BV1test",
            "title": "Test",
            "_bilibili": {"parameter": "bvid=BV1test", "pages": [{"cid": 42}]},
        })
        self.assertNotIn("_bilibili", compact)
        self.assertNotIn("cid", json.dumps(compact))

    def test_bilibili_metadata_does_not_guess_spoken_language(self):
        import ingest_media

        def fake_fetch(url, _referer):
            if "/view?" in url:
                return {"code": 0, "data": {
                    "bvid": "BV1test", "title": "中文标题", "duration": 60,
                    "owner": {}, "stat": {}, "pages": [{"page": 1, "cid": 42}],
                }}
            return {"code": 0, "data": {"subtitle": {"subtitles": []}}}

        original_fetch = ingest_media.fetch_json
        ingest_media.fetch_json = fake_fetch
        try:
            metadata, _ = bilibili_public_metadata("https://www.bilibili.com/video/BV1test")
            self.assertIsNone(metadata["language"])
        finally:
            ingest_media.fetch_json = original_fetch

    def test_bundle_is_not_classified_as_downloaded_media_other(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bundle.json").write_text("{}", encoding="utf-8")
            self.assertEqual(classify_files(root)["other"], [])

    def test_bilibili_public_audio_fallback_handles_multiple_parts(self):
        import ingest_media
        metadata = {
            "id": "BV1test",
            "webpage_url": "https://www.bilibili.com/video/BV1test",
            "_bilibili": {
                "parameter": "bvid=BV1test",
                "pages": [{"page": 1, "cid": 11}, {"page": 2, "cid": 22}],
            },
        }

        def fake_fetch(_url, _referer):
            return {"code": 0, "data": {"dash": {"audio": [{"bandwidth": 64000, "baseUrl": "https://signed.example/audio?token=secret"}]}}}

        def fake_run(args, _cwd):
            Path(args[-1]).write_bytes(b"audio")
            return subprocess.CompletedProcess(args, 0, "", "")

        original_fetch, original_run = ingest_media.fetch_json, ingest_media.run
        ingest_media.fetch_json, ingest_media.run = fake_fetch, fake_run
        try:
            with tempfile.TemporaryDirectory() as folder:
                files, warnings = write_bilibili_audio(metadata, Path(folder), metadata["webpage_url"], "mp3", False)
                self.assertEqual(len(files), 2)
                self.assertEqual(warnings, [])
                self.assertTrue(all(Path(path).is_file() for path in files))
                self.assertNotIn("secret", json.dumps(warnings))
        finally:
            ingest_media.fetch_json, ingest_media.run = original_fetch, original_run

    def test_chunk_transcripts_restore_global_timeline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            transcript_dir = root / "transcripts"
            transcript_dir.mkdir()
            manifest = {
                "chunks": [
                    {"sequence": 1, "file": str(root / "source-01-chunk-000.ogg"), "global_offset_seconds": 0},
                    {"sequence": 2, "file": str(root / "source-02-chunk-000.ogg"), "global_offset_seconds": 10},
                ]
            }
            manifest_path = root / "audio-chunks.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            for stem, text in (("source-01-chunk-000", "first"), ("source-02-chunk-000", "second")):
                (transcript_dir / f"{stem}.transcript.json").write_text(json.dumps({
                    "segments": [{"start": 1, "end": 2, "speaker": "A", "text": text}]
                }), encoding="utf-8")
            result = combine(manifest_path, transcript_dir)
            self.assertEqual([item["start_seconds"] for item in result["segments"]], [1.0, 11.0])
            self.assertEqual(result["segments"][1]["text"], "second")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_audio_chunk_manifest_has_ordered_offsets_and_safe_sizes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "tone.wav"
            generated = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=2.2", str(source),
            ], capture_output=True)
            self.assertEqual(generated.returncode, 0, msg=generated.stderr.decode(errors="replace"))
            manifest = split_audio([source], root / "chunks", 1.0, 16, 1024 * 1024, False)
            self.assertGreaterEqual(len(manifest["chunks"]), 2)
            offsets = [item["global_offset_seconds"] for item in manifest["chunks"]]
            self.assertEqual(offsets, sorted(offsets))
            self.assertTrue(all(item["size_bytes"] < 1024 * 1024 for item in manifest["chunks"]))

    def test_local_transcription_adapter_is_timestamped_and_zero_key(self):
        class FakeModel:
            def transcribe(self, _audio, **_options):
                segment = SimpleNamespace(start=1.25, end=3.5, text=" 本地转写成功 ", words=None)
                info = SimpleNamespace(language="zh", language_probability=0.99, duration=4.0)
                return iter([segment]), info

        args = SimpleNamespace(
            beam_size=5, no_vad=False, word_timestamps=False,
            task="transcribe", language="auto", model="small",
        )
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / "sample.ogg"
            audio.write_bytes(b"fake")
            result = transcribe_one(FakeModel(), audio, args)
            self.assertEqual(result["provider"], "local:faster-whisper")
            self.assertFalse(result["speaker_diarization"])
            self.assertEqual(result["segments"][0]["start"], 1.25)
            self.assertEqual(result["segments"][0]["text"], "本地转写成功")

    def test_local_transcription_dry_run_needs_no_api_key_or_dependency(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root / "sample.ogg"
            audio.write_bytes(b"fake")
            result = self.invoke(
                "transcribe_local.py", audio, "--output-dir", root / "out", "--dry-run"
            )
            self.assertFalse(result["api_key_required"])
            self.assertEqual(result["provider"], "local:faster-whisper")


if __name__ == "__main__":
    unittest.main()
