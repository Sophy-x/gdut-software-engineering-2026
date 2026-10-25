"""测试 Windows 语音服务的可预测部分，不访问麦克风或扬声器。"""

import base64
import subprocess
from types import SimpleNamespace

import pytest

from core.commands import voice_input
from core.voice import (
    LowConfidenceSpeech,
    NoSpeechDetected,
    VoiceError,
    WindowsSpeech,
)


def test_recognize_decodes_utf8_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    transcript = "请整理项目文件"
    payload = '{"text":"请整理项目文件","confidence":0.91}'
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    monkeypatch.setattr(
        "core.voice._run_powershell",
        lambda script, timeout: subprocess.CompletedProcess([], 0, encoded, ""),
    )

    assert WindowsSpeech()._recognize_sync() == transcript


def test_recognize_reports_when_no_speech(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "core.voice._run_powershell",
        lambda script, timeout: subprocess.CompletedProcess([], 2, "", ""),
    )

    with pytest.raises(NoSpeechDetected, match="No speech detected"):
        WindowsSpeech()._recognize_sync()


def test_recognize_reports_low_confidence_speech(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = '{"text":"请整理项目文件","confidence":0.31}'
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    monkeypatch.setattr(
        "core.voice._run_powershell",
        lambda script, timeout: subprocess.CompletedProcess([], 0, encoded, ""),
    )

    with pytest.raises(LowConfidenceSpeech, match="confidence was too low") as caught:
        WindowsSpeech()._recognize_sync()

    assert caught.value.transcript == "请整理项目文件"
    assert caught.value.confidence == 0.31


def test_recognize_reports_service_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "core.voice._run_powershell",
        lambda script, timeout: subprocess.CompletedProcess([], 1, "", "No microphone"),
    )

    with pytest.raises(VoiceError, match="No microphone"):
        WindowsSpeech()._recognize_sync()


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

        async def recognize(self) -> str:
            return "识别出的任务"

    screen = FakeScreen()
    monkeypatch.setattr(voice_input, "WindowsSpeech", FakeSpeech)

    await voice_input.listen_command(SimpleNamespace(screen=screen))

    assert screen.draft == "识别出的任务"
    assert screen.entries == [("tool", "Speech recognized. Review the draft and press Enter.")]
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
