import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from combine_chunk_transcripts import combine
from runtime_utils import atomic_write_json, file_fingerprint
from transcribe_local import cache_settings, transcribe_one, valid_cached_transcript


def args():
    return argparse.Namespace(model="small", language="zh", task="transcribe", beam_size=1,
                              batch_size=8, word_timestamps=False, no_vad=False)


def empty_result(duration=20.0, retained=0.0, no_vad=False):
    options = args()
    options.no_vad = no_vad
    model = SimpleNamespace(transcribe=lambda *_a, **_k: (
        iter([]), SimpleNamespace(language="zh", duration=duration, duration_after_vad=retained)
    ))
    return transcribe_one(model, Path("outro.ogg"), options)


class NoSpeechChunkTests(unittest.TestCase):
    def test_completed_vad_no_speech_result_retains_duration_without_text(self):
        result = empty_result()
        self.assertEqual(result["segments"], [])
        self.assertFalse(result["speech_detected"])
        self.assertTrue(result["no_speech"])
        self.assertEqual(result["duration_seconds"], 20.0)
        self.assertEqual(result["duration_after_vad_seconds"], 0.0)

    def test_empty_results_without_positive_decoding_and_zero_vad_are_rejected(self):
        for duration, retained, no_vad in (
            (None, 0, False), (0, 0, False), (-1, 0, False), (float("nan"), 0, False),
            (20, None, False), (20, 1, False), (20, False, False), (20, 0, True),
        ):
            with self.subTest(duration=duration, retained=retained, no_vad=no_vad):
                with self.assertRaisesRegex(RuntimeError, "without confirmed VAD"):
                    empty_result(duration, retained, no_vad)

    def test_no_speech_cache_requires_marker_fingerprint_and_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root / "outro.ogg"
            audio.write_bytes(b"decoded audio")
            target = root / "outro.transcript.json"
            result = empty_result()
            result["cache"] = {"source": file_fingerprint(audio), "settings": cache_settings(args())}
            atomic_write_json(target, result)
            self.assertTrue(valid_cached_transcript(target, audio, args())[0])
            changed = args()
            changed.language = "en"
            self.assertEqual(valid_cached_transcript(target, audio, changed), (False, "settings_changed"))
            result.pop("no_speech")
            atomic_write_json(target, result)
            self.assertFalse(valid_cached_transcript(target, audio, args())[0])
            result["no_speech"] = True
            atomic_write_json(target, result)
            audio.write_bytes(b"different audio")
            self.assertEqual(valid_cached_transcript(target, audio, args()), (False, "source_changed"))

    def prepare_pair(self, root, first):
        manifest = root / "audio-chunks.json"
        atomic_write_json(manifest, {"chunks": [
            {"sequence": 1, "file": "speech.ogg", "global_offset_seconds": 0},
            {"sequence": 2, "file": "outro.ogg", "global_offset_seconds": 300},
        ]})
        atomic_write_json(root / "speech.transcript.json", first)
        atomic_write_json(root / "outro.transcript.json", empty_result())
        return manifest

    def test_no_speech_tail_is_complete_and_never_creates_a_text_segment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.prepare_pair(root, {"segments": [{"start": 1, "end": 2, "text": "Goodbye."}]})
            result = combine(manifest, root)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["completed_chunks"], 2)
            self.assertEqual(len(result["segments"]), 1)
            self.assertEqual(result["segments"][0]["text"], "Goodbye.")
            self.assertEqual(result["no_speech_chunks"][0]["start_seconds"], 300)
            self.assertEqual(result["no_speech_chunks"][0]["end_seconds"], 320)

    def test_unmarked_empty_tail_is_rejected_even_when_other_chunks_have_speech(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.prepare_pair(root, {"segments": [{"start": 1, "end": 2, "text": "Goodbye."}]})
            atomic_write_json(root / "outro.transcript.json", {"segments": []})
            with self.assertRaisesRegex(ValueError, "without confirmed VAD"):
                combine(manifest, root)

    def test_all_no_speech_is_recorded_but_cannot_become_an_analyzable_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.prepare_pair(root, empty_result())
            result = combine(manifest, root)
            self.assertEqual(result["completed_chunks"], 2)
            self.assertFalse(result["speech_detected"])
            self.assertEqual(result["segments"], [])
            self.assertEqual(len(result["no_speech_chunks"]), 2)
            source = root / "combined.json"
            atomic_write_json(source, result)
            normalized = subprocess.run([
                sys.executable, str(SCRIPTS / "normalize_transcript.py"), str(source),
                "--output-dir", str(root / "normalized"),
            ], capture_output=True)
            self.assertNotEqual(normalized.returncode, 0)
            self.assertFalse((root / "normalized" / "transcript.json").exists())


if __name__ == "__main__":
    unittest.main()
