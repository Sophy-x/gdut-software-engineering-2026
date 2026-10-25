"""测试 Windows 语音服务的可预测部分，不访问麦克风或扬声器。"""

import base64
import subprocess
import sys
from types import SimpleNamespace

import pytest

from core.commands import voice_input
from core.voice import (
    NoSpeechDetected,
    SpeechRecognition,
    VoiceError,
    WhisperSpeech,
    WindowsSpeech,
)


def test_whisper_recognizes_audio_and_detects_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import numpy as np

    class FakeSoundDevice:
        @staticmethod
        def rec(*args, **kwargs):
            return np.ones((kwargs["channels"],), dtype=np.float32)

    class FakeModel:
        def transcribe(self, audio, **kwargs):
            assert kwargs["language"] is None
            return iter([SimpleNamespace(text=" 请整理项目文件 ")]), SimpleNamespace(
                language="zh", language_probability=0.97
            )

    class FakeFasterWhisper:
        WhisperModel = lambda *args, **kwargs: FakeModel()

    monkeypatch.setitem(sys.modules, "sounddevice", FakeSoundDevice)
    monkeypatch.setitem(sys.modules, "faster_whisper", FakeFasterWhisper)
    import core.voice as voice

    voice._MODEL_CACHE.clear()
    result = WhisperSpeech(record_seconds=1)._recognize_sync()

    assert result == SpeechRecognition("请整理项目文件", "zh", 0.97)


def test_whisper_reports_silent_recording(monkeypatch: pytest.MonkeyPatch) -> None:
    import numpy as np

    class FakeSoundDevice:
        @staticmethod
        def rec(*args, **kwargs):
            return np.zeros((kwargs["channels"],), dtype=np.float32)

    monkeypatch.setitem(sys.modules, "sounddevice", FakeSoundDevice)

    with pytest.raises(NoSpeechDetected, match="No speech detected"):
        WhisperSpeech(record_seconds=1)._recognize_sync()


def test_whisper_reports_recording_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingSoundDevice:
        @staticmethod
        def rec(*args, **kwargs):
            raise OSError("No microphone")

    monkeypatch.setitem(sys.modules, "sounddevice", FailingSoundDevice)

    with pytest.raises(VoiceError, match="No microphone"):
        WhisperSpeech(record_seconds=1)._recognize_sync()


def test_speech_output_reports_service_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "core.voice._run_powershell",
        lambda script, timeout: subprocess.CompletedProcess([], 1, "", "No microphone"),
    )

    with pytest.raises(VoiceError, match="No microphone"):
        WindowsSpeech()._speak_sync("测试")


def test_speak_passes_utf8_text_to_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, float]] = []

    def fake_run(script: str, *, timeout: float):
        calls.append((script, timeout))
        return subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr("core.voice._run_powershell", fake_run)

    WindowsSpeech()._speak_sync("处理完成")

    assert len(calls) == 1
    assert calls[0][1] == 120
    assert base64.b64encode("处理完成".encode("utf-8")).decode("ascii") in calls[0][0]


@pytest.mark.asyncio
async def test_listen_command_places_transcript_in_editable_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeScreen:
        def __init__(self) -> None:
            self.entries: list[tuple[str, str]] = []
            self.draft = ""
            self.status: list[str] = []

        def add_entry(self, role: str, content: str) -> None:
            self.entries.append((role, content))

        def set_input_text(self, text: str) -> None:
            self.draft = text

        def set_status_message(self, message: str) -> None:
            self.status.append(message)

    class FakeSpeech:
        @staticmethod
        def available() -> bool:
            return True

        async def recognize(self) -> SpeechRecognition:
            return SpeechRecognition("识别出的任务", "zh", 0.94)

    screen = FakeScreen()
    monkeypatch.setattr(voice_input, "WhisperSpeech", FakeSpeech)

    await voice_input.listen_command(SimpleNamespace(screen=screen))

    assert screen.draft == "识别出的任务"
    assert screen.entries == [
        (
            "tool",
            "Speech recognized (zh, language probability 0.94). "
            "Review the draft and press Enter.",
        )
    ]
    assert screen.status == ["Listening for speech...", ""]


@pytest.mark.asyncio
async def test_voice_command_toggles_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeScreen:
        voice_output_enabled = False

        def __init__(self) -> None:
            self.entries: list[tuple[str, str]] = []

        def add_entry(self, role: str, content: str) -> None:
            self.entries.append((role, content))

        def set_voice_output_enabled(self, enabled: bool) -> None:
            self.voice_output_enabled = enabled

    class FakeSpeech:
        @staticmethod
        def available() -> bool:
            return True

    screen = FakeScreen()
    from core.commands import voice_output

    monkeypatch.setattr(voice_output, "WindowsSpeech", FakeSpeech)

    context = SimpleNamespace(screen=screen, arguments="on")
    await voice_output.voice_output_command(context)

    assert screen.voice_output_enabled is True
    assert screen.entries == [("tool", "Voice output enabled.")]
