import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from transcribe_local import main


class TranscriptionRuntimeTests(unittest.TestCase):
    def invoke_with_incompatible_decoder(self, extra_args):
        model = Mock()
        modules = {
            "av": SimpleNamespace(__version__="19.0.1"),
            "faster_whisper": SimpleNamespace(
                WhisperModel=model, BatchedInferencePipeline=Mock()
            ),
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root / "audio with spaces.wav"
            audio.write_bytes(b"RIFF")
            output = root / "output"
            argv = ["transcribe_local.py", str(audio), "--output-dir", str(output), *extra_args]
            stderr = io.StringIO()
            with patch.dict(sys.modules, modules), patch.object(sys, "argv", argv), \
                    patch("transcribe_local.shutil.which", return_value="uv"), \
                    patch("transcribe_local.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run, \
                    contextlib.redirect_stderr(stderr):
                status = main()
            model.assert_not_called()
            self.assertFalse(output.exists(), "Incompatible dependencies must be resolved before model loading or outputs")
            return status, stderr.getvalue(), run

    def test_installed_pyav_19_bootstraps_compatible_environment(self):
        status, _, run = self.invoke_with_incompatible_decoder(["--bootstrap"])
        self.assertEqual(status, 0)
        command = run.call_args.args[0]
        requirements = [command[i + 1] for i, value in enumerate(command) if value == "--with"]
        self.assertIn("faster-whisper==1.2.1", requirements)
        self.assertIn("av>=11,<19", requirements)
        self.assertNotIn("--bootstrap", command)
        self.assertIn("--_uv-child", command)
        self.assertTrue(any("audio with spaces.wav" in value for value in command))

    def test_installed_pyav_19_without_bootstrap_reports_actionable_error(self):
        status, stderr, run = self.invoke_with_incompatible_decoder([])
        self.assertEqual(status, 2)
        result = json.loads(stderr)
        self.assertEqual(result["stage"], "dependency")
        self.assertIn("PyAV 19.0.1", result["error"])
        self.assertIn("av>=11,<19", result["error"])
        run.assert_not_called()

    def test_incompatible_bootstrap_child_does_not_recurse(self):
        status, stderr, run = self.invoke_with_incompatible_decoder(["--bootstrap", "--_uv-child"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stderr)["stage"], "dependency")
        run.assert_not_called()

    def test_cpu_threads_reach_model_without_changing_transcript_cache(self):
        settings = []
        for threads in (0, 8):
            def transcribe(_audio, **_options):
                return iter([SimpleNamespace(start=0, end=1, text="A complete sentence.", words=None)]), \
                    SimpleNamespace(language="en", duration=1)

            model = Mock(return_value=SimpleNamespace(transcribe=transcribe))
            modules = {
                "av": SimpleNamespace(__version__="18.1.0"),
                "faster_whisper": SimpleNamespace(
                    WhisperModel=model, BatchedInferencePipeline=Mock()
                ),
            }
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                audio = root / "audio.wav"
                audio.write_bytes(b"RIFF")
                output = root / "output"
                argv = [
                    "transcribe_local.py", str(audio), "--output-dir", str(output),
                    "--device", "cpu", "--cpu-threads", str(threads),
                ]
                with patch.dict(sys.modules, modules), patch.object(sys, "argv", argv), \
                        contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(), 0)
                options = model.call_args.kwargs
                if threads:
                    self.assertEqual(options["cpu_threads"], 8)
                else:
                    self.assertNotIn("cpu_threads", options)
                transcript = json.loads((output / "audio.transcript.json").read_text(encoding="utf-8"))
                settings.append(transcript["cache"]["settings"])
        self.assertEqual(settings[0], settings[1])


if __name__ == "__main__":
    unittest.main()
