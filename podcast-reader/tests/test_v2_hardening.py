import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from apply_diarization import apply as apply_diarization
from assess_transcript import assess
from build_release import release_files
from cleanup_bundle import cleanup
from doctor import inspect
from evidence_validator import validate_evidence
from ingest_media import download_public_stream, duration_is_complete, subtitle_download_candidates
from install_skill import install, rollback
from prepare_audio_chunks import split_audio
from render_reader import timestamp_url
from release_check import check as release_check
from runtime_utils import atomic_write_json, file_fingerprint
from transcribe_local import cache_settings, quarantine_invalid_cache, valid_cached_transcript
from translate_transcript import apply_translation
from validate_notes import validate as validate_notes


class V2HardeningTests(unittest.TestCase):
    def run_script(self, name, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, msg=result.stderr or result.stdout)
        stream = result.stdout if result.stdout.strip() else result.stderr
        return json.loads(stream)

    def prepared_episode(self, root: Path) -> Path:
        episode = root / "episode"
        self.run_script("prepare_episode.py", FIXTURES / "sample.srt", "--output-dir", episode)
        return episode

    def finalized_episode(self, root: Path) -> Path:
        episode = self.prepared_episode(root)
        shutil.copy2(FIXTURES / "golden-analysis.md", episode / "analysis.md")
        shutil.copy2(FIXTURES / "golden-evidence.json", episode / "evidence.json")
        self.run_script("finalize_bundle.py", episode)
        return episode

    def test_process_needs_selection_uses_action_required_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_script("process_episode.py", FIXTURES / "sample.rss", "--output-root", folder, "--no-transcribe", expected=3)
            self.assertEqual(result["status"], "needs_selection")

    def test_private_network_url_is_rejected_before_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_script("fetch_audio.py", "http://127.0.0.1:9/audio.mp3", "--output-dir", folder, expected=1)
            self.assertEqual(result["stage"], "security")

    def test_doctor_distinguishes_bootstrap_from_installed_readiness(self):
        def command(name, _args):
            return {"available": name in {"ffmpeg", "ffprobe", "uv"}, "path": name if name in {"ffmpeg", "ffprobe", "uv"} else None, "version": "test"}
        with tempfile.TemporaryDirectory() as folder, patch("doctor.command_check", side_effect=command), patch("doctor.importlib.util.find_spec", return_value=None):
            result = inspect(Path(folder) / "missing" / "nested")
            self.assertEqual(result["readiness"], "bootstrap_ready")
            self.assertFalse(result["capabilities"]["full_pipeline_offline_ready"])
            self.assertTrue(result["output"]["writable"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
    def test_incomplete_chunk_cache_is_rebuilt_instead_of_silently_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root / "sample.wav"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-y", str(audio)], check=True)
            output = root / "chunks"
            first = split_audio([audio], output, 1.0, 24, 5 * 1024 * 1024, False)
            self.assertGreaterEqual(len(first["chunks"]), 3)
            (output / first["chunks"][-1]["relative_file"]).unlink()
            second = split_audio([audio], output, 1.0, 24, 5 * 1024 * 1024, False)
            self.assertEqual(second["cache"], "rebuilt")
            self.assertIn("chunk_file_missing_or_empty", second["cache_validation"]["reasons"])
            self.assertTrue(all((output / item["relative_file"]).is_file() for item in second["chunks"]))

    def test_corrupt_transcript_cache_is_quarantined(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root / "chunk.ogg"
            audio.write_bytes(b"audio")
            target = root / "chunk.transcript.json"
            target.write_text("{broken", encoding="utf-8")
            args = argparse.Namespace(model="small", language="auto", task="transcribe", beam_size=1, batch_size=4, word_timestamps=False, no_vad=False)
            valid, reason = valid_cached_transcript(target, audio, args)
            self.assertFalse(valid)
            quarantined = quarantine_invalid_cache(target, reason)
            self.assertFalse(target.exists())
            self.assertTrue(quarantined.is_file())
            document = {"schema_version": "2.0", "status": "complete", "segments": [{"text": "ok"}], "cache": {"source": file_fingerprint(audio), "settings": cache_settings(args)}}
            atomic_write_json(target, document)
            self.assertTrue(valid_cached_transcript(target, audio, args)[0])

    def test_evidence_rejects_fabricated_quote_and_invalid_enum(self):
        transcript = {"segments": [{"segment_id": 1, "start_seconds": 0, "end_seconds": 5, "text": "Exact source words."}]}
        evidence = {"schema_version": "2.0", "chapters": [], "claims": [{"claim": "x", "kind": "guess", "support": "stated", "confidence": "high", "verification": "not_checked", "evidence": [{"segment_ids": [1], "start": "00:00:00", "end": "00:00:05"}]}], "quotes": [{"text": "Invented words", "start": "00:00:00", "end": "00:00:05", "segment_ids": [1]}], "actions": [], "entities": [], "glossary": [], "visual_evidence": [], "limitations": []}
        result = validate_evidence(evidence, transcript)
        self.assertFalse(result["valid"])
        self.assertTrue(any("quote text" in error for error in result["errors"]))
        self.assertTrue(any("invalid kind" in error for error in result["errors"]))

    def test_markdown_rejects_timestamp_beyond_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.prepared_episode(root)
            report = root / "bad.md"
            report.write_text((FIXTURES / "golden-analysis.md").read_text(encoding="utf-8").replace("00:00:18", "09:00:00"), encoding="utf-8")
            result = validate_notes(report, strict=True, transcript_path=episode / "transcript.json")
            self.assertFalse(result["valid"])
            self.assertIn("timestamp_ranges_valid", result["failures"])

    def test_share_export_removes_local_paths_and_full_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.finalized_episode(root)
            output = root / "share.zip"
            self.run_script("export_bundle.py", episode, "--output", output)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertFalse(any(Path(name).name.startswith("transcript") for name in names))
                joined = b"\n".join(archive.read(name) for name in names if name.endswith((".json", ".md", ".html")))
                self.assertNotIn(str(root).encode(), joined)
                self.assertIn("podcast-reader-bundle/reader.html", names)

    def test_translation_requires_complete_segment_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.prepared_episode(root)
            transcript = json.loads((episode / "transcript.json").read_text(encoding="utf-8"))
            translation = {"target_language": "en", "segments": [{"segment_id": item["segment_id"], "text": f"Translated {item['segment_id']}"} for item in transcript["segments"]]}
            result = apply_translation(transcript, translation, "en", root / "translations")
            self.assertEqual(result["segments"], transcript["segment_count"])
            self.assertTrue((root / "translations" / "transcript.en.vtt").is_file())

    def test_translation_request_is_explicit_action_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.prepared_episode(root)
            result = self.run_script("translate_transcript.py", episode / "transcript.json", "--target-language", "ja", expected=3)
            self.assertEqual(result["status"], "awaiting_agent_translation")
            self.assertTrue(Path(result["request"]).is_file())

    def test_diarization_adapter_assigns_speakers_by_overlap(self):
        transcript = {"segments": [{"segment_id": 1, "start_seconds": 0.0, "end_seconds": 4.0, "text": "one"}, {"segment_id": 2, "start_seconds": 4.0, "end_seconds": 8.0, "text": "two"}]}
        result = apply_diarization(transcript, [{"start": 0.0, "end": 4.0, "speaker": "Speaker 1"}, {"start": 4.0, "end": 8.0, "speaker": "Speaker 2"}], 0.35)
        self.assertEqual([item["speaker"] for item in result["segments"]], ["Speaker 1", "Speaker 2"])
        self.assertEqual(result["diarization_metrics"]["coverage"], 1.0)

    def test_cleanup_is_preview_first_and_preserves_knowledge(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.prepared_episode(root)
            cache = episode / "audio-chunks"
            cache.mkdir()
            (cache / "cache.ogg").write_bytes(b"123")
            preview = cleanup(episode, "cache", False)
            self.assertEqual(preview["status"], "preview")
            self.assertTrue(cache.exists())
            cleanup(episode, "cache", True)
            self.assertFalse(cache.exists())
            self.assertTrue((episode / "transcript.json").is_file())

    def test_installer_blocks_downgrade_and_supports_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "skills"
            self.assertTrue(install(target, False)["valid"])
            self.assertFalse((target / "podcast-reader" / "tests").exists())
            self.assertFalse((target / "podcast-reader" / "scripts" / "build_release.py").exists())
            self.assertTrue(install(target, True)["valid"])
            self.assertTrue(rollback(target, "latest")["valid"])
            (target / "podcast-reader" / "VERSION").write_text("99.0.0", encoding="utf-8")
            blocked = install(target, True)
            self.assertFalse(blocked["valid"])
            self.assertIn("refusing downgrade", blocked["error"])

    def test_platform_timestamp_links_are_seekable(self):
        self.assertIn("t=90s", timestamp_url("https://www.youtube.com/watch?v=x", 90))
        self.assertIn("t=90", timestamp_url("https://www.bilibili.com/video/BV1x", 90))

    def test_subtitle_fallback_prefers_human_then_source_language(self):
        metadata = {
            "language": "en",
            "subtitles": {"zh-CN": [{}], "en": [{}]},
            "automatic_captions": {"zh-Hans": [{}], "en-orig": [{}]},
        }
        candidates = subtitle_download_candidates(metadata, "zh-Hans,en,all,-live_chat")
        self.assertEqual(candidates[:2], [("zh-CN", "human"), ("en", "human")])
        self.assertEqual(candidates[2], ("en-orig", "automatic"))

    def test_public_stream_resumes_after_early_eof_and_verifies_size(self):
        payload = b"abcdefghij"
        calls = 0

        class FakeResponse:
            status = 206

            def __init__(self, start, end, body):
                self.headers = {"Content-Range": f"bytes {start}-{end}/{len(payload)}"}
                self.body = body
                self.offset = 0

            def getcode(self):
                return self.status

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                if self.offset >= len(self.body):
                    return b""
                end = len(self.body) if size < 0 else min(len(self.body), self.offset + size)
                result = self.body[self.offset:end]
                self.offset = end
                return result

        def fake_open(request, timeout=90):
            nonlocal calls
            calls += 1
            match = __import__("re").match(r"bytes=(\d+)-(\d+)", request.get_header("Range"))
            start = int(match.group(1))
            end = min(int(match.group(2)), len(payload) - 1)
            body = payload[start:end + 1]
            if calls == 1:
                body = body[:2]
            return FakeResponse(start, end, body)

        with tempfile.TemporaryDirectory() as folder, patch("ingest_media.safe_urlopen", side_effect=fake_open):
            target = Path(folder) / "media.bin"
            result = download_public_stream("https://example.com/media", target, "https://example.com", chunk_size=4)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(result["expected_size_bytes"], len(payload))
            self.assertGreater(calls, 2)

    def test_duration_completeness_rejects_truncated_bilibili_audio(self):
        self.assertTrue(duration_is_complete(5899.52, 5900))
        self.assertFalse(duration_is_complete(1069.952, 5900))

    def test_transcript_quality_flags_cjk_within_segment_repetition(self):
        document = {
            "segments": [
                {"segment_id": 1, "start_seconds": 0, "end_seconds": 5, "text": "这是一段正常的中文访谈内容。", "confidence": 0.9},
                {"segment_id": 2, "start_seconds": 5, "end_seconds": 10, "text": "嗯 " * 40, "confidence": 0.8},
                {"segment_id": 3, "start_seconds": 10, "end_seconds": 15, "text": "45,000,000" * 12, "confidence": 0.7},
            ]
        }
        result = assess(document)
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["metrics"]["pathological_segments"], 2)
        self.assertEqual(result["metrics"]["pathological_segment_ids"], [2, 3])
        self.assertGreaterEqual(result["metrics"]["max_repeated_span"], 40)

    def test_release_invariants_use_single_version_source(self):
        result = release_check()
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["version"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())

    def test_release_files_use_repo_relative_exclusions(self):
        names = {path.relative_to(ROOT.parent).as_posix() for path in release_files()}
        self.assertIn("README.md", names)
        self.assertIn("podcast-reader/SKILL.md", names)
        self.assertFalse(any(name.startswith("dist/") or "/__pycache__/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
