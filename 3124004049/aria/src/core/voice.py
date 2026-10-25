"""跨平台语音输入与 Windows 语音输出。"""

import asyncio
import base64
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path


class VoiceError(RuntimeError):
    """语音设备、模型或语音服务不可用时抛出。"""


class NoSpeechDetected(VoiceError):
    """录音窗口内没有检测到有效语音。"""


@dataclass(frozen=True)
class SpeechRecognition:
    """一次 Whisper 识别结果及其自动检测出的语言。"""

    text: str
    language: str
    language_probability: float


_WHISPER_MODEL_SIZE = os.environ.get("ARIA_WHISPER_MODEL", "base")
_WHISPER_DEVICE = os.environ.get("ARIA_WHISPER_DEVICE", "cpu")
_WHISPER_COMPUTE_TYPE = os.environ.get("ARIA_WHISPER_COMPUTE_TYPE", "int8")
_RECORD_SECONDS = float(os.environ.get("ARIA_VOICE_RECORD_SECONDS", "12"))
_INPUT_DEVICE = os.environ.get("ARIA_VOICE_INPUT_DEVICE")
_SAMPLE_RATE = 16_000
_MIN_AUDIO_LEVEL = 0.005
_MODEL_CACHE: dict[tuple[str, str, str], object] = {}
_MODEL_LOCK = threading.Lock()


class WhisperSpeech:
    """使用 faster-whisper 进行跨平台麦克风录音和自动语言识别。"""

    def __init__(
        self,
        model_size: str = _WHISPER_MODEL_SIZE,
        device: str = _WHISPER_DEVICE,
        compute_type: str = _WHISPER_COMPUTE_TYPE,
        record_seconds: float = _RECORD_SECONDS,
        input_device: str | int | None = _INPUT_DEVICE,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.record_seconds = record_seconds
        self.input_device = input_device
        self._active_stop_event: threading.Event | None = None
        self._active_lock = threading.Lock()

    @staticmethod
    def available() -> bool:
        """检查 faster-whisper、sounddevice 和 numpy 是否已安装。"""

        try:
            import faster_whisper  # noqa: F401
            import numpy  # noqa: F401
            import sounddevice  # noqa: F401
        except (ImportError, OSError):
            return False
        return True

    async def recognize(self) -> SpeechRecognition:
        """录音并使用 Whisper 自动检测语言后返回转写结果。"""

        stop_event = threading.Event()
        with self._active_lock:
            if self._active_stop_event is not None:
                raise VoiceError("Voice recording is already active")
            self._active_stop_event = stop_event
        try:
            return await asyncio.to_thread(self._recognize_sync, stop_event)
        except asyncio.CancelledError:
            stop_event.set()
            raise
        finally:
            stop_event.set()
            with self._active_lock:
                if self._active_stop_event is stop_event:
                    self._active_stop_event = None

    def stop(self) -> None:
        """请求停止当前录音；没有录音时不执行任何操作。"""

        with self._active_lock:
            stop_event = self._active_stop_event
        if stop_event is not None:
            stop_event.set()

    def _recognize_sync(
        self, stop_event: threading.Event | None = None
    ) -> SpeechRecognition:
        """同步录制一段音频并运行一次 Whisper 转写。"""

        try:
            import numpy as np
            import sounddevice as sd
        except (ImportError, OSError) as exc:
            raise VoiceError(
                "Whisper voice input is not installed; run `uv sync --frozen`"
            ) from exc

        if self.record_seconds <= 0:
            raise VoiceError("ARIA_VOICE_RECORD_SECONDS must be greater than zero")

        active_stop_event = stop_event or threading.Event()
        try:
            audio = self._record_audio(sd, np, active_stop_event)
        except Exception as exc:
            raise VoiceError(
                f"Failed to record from the default microphone: {exc}"
            ) from exc

        if audio.size == 0 or float(np.max(np.abs(audio))) < _MIN_AUDIO_LEVEL:
            raise NoSpeechDetected(
                f"No speech detected in the {self.record_seconds:g}-second recording"
            )

        try:
            model = self._get_model()
            segments, info = model.transcribe(
                audio,
                language=None,
                beam_size=5,
                vad_filter=True,
            )
            text = "".join(segment.text for segment in segments).strip()
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(f"Whisper transcription failed: {exc}") from exc

        if not text:
            raise NoSpeechDetected("Whisper did not find recognizable speech")
        return SpeechRecognition(
            text=text,
            language=str(info.language),
            language_probability=float(info.language_probability),
        )

    def _record_audio(self, sd, np, stop_event: threading.Event):
        """以可取消的流式方式采集固定时长的单声道音频。"""

        chunks = []

        def on_audio(indata, frames, callback_time, status) -> None:
            """复制音频块，避免回调返回后底层缓冲区被复用。"""

            if not stop_event.is_set():
                chunks.append(indata.copy())

        stream_kwargs = {
            "samplerate": _SAMPLE_RATE,
            "channels": 1,
            "dtype": "float32",
            "callback": on_audio,
        }
        if self.input_device is not None:
            stream_kwargs["device"] = self.input_device

        deadline = time.monotonic() + self.record_seconds
        with sd.InputStream(**stream_kwargs):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                if stop_event.wait(min(0.05, remaining)):
                    break

        if not chunks:
            return np.empty(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).astype(np.float32, copy=False).reshape(-1)

    def _get_model(self):
        """懒加载并缓存模型，避免每次 /listen 都重新加载。"""

        key = (self.model_size, self.device, self.compute_type)
        with _MODEL_LOCK:
            model = _MODEL_CACHE.get(key)
            if model is None:
                try:
                    from faster_whisper import WhisperModel

                    model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                except Exception as exc:
                    raise VoiceError(
                        f"Failed to load Whisper model '{self.model_size}': {exc}"
                    ) from exc
                _MODEL_CACHE[key] = model
            return model


class WindowsSpeech:
    """封装 Windows PowerShell 的语音合成 API。"""

    _SYNTHESIZE_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__TEXT__'))
$synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synthesizer.Speak($text)
} finally {
    $synthesizer.Dispose()
}
"""

    @staticmethod
    def available() -> bool:
        """检查 Windows PowerShell 是否可用。"""

        if os.name != "nt":
            return False
        if shutil.which("powershell.exe"):
            return True
        windows_dir = os.environ.get("WINDIR")
        return bool(
            windows_dir
            and (
                Path(windows_dir)
                / "System32"
                / "WindowsPowerShell"
                / "v1.0"
                / "powershell.exe"
            ).is_file()
        )

    async def speak(self, text: str) -> None:
        """使用 Windows 默认语音合成器朗读文本。"""

        if not text.strip():
            return
        await asyncio.to_thread(self._speak_sync, text)

    def _speak_sync(self, text: str) -> None:
        """执行一次 Windows 语音合成。"""

        encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
        result = _run_powershell(
            self._SYNTHESIZE_SCRIPT.replace("__TEXT__", encoded_text), timeout=120
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "speech synthesis failed"
            raise VoiceError(detail)


def _run_powershell(script: str, *, timeout: float) -> subprocess.CompletedProcess[str]:
    """通过 Base64 编码的 PowerShell 脚本避免命令行转义问题。"""

    executable = shutil.which("powershell.exe")
    if executable is None:
        windows_dir = os.environ.get("WINDIR")
        candidate = (
            Path(windows_dir)
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "powershell.exe"
            if windows_dir
            else None
        )
        if candidate is None or not candidate.is_file():
            raise VoiceError("Windows PowerShell is not available")
        executable = str(candidate)
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        return subprocess.run(
            [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded_script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VoiceError(f"Windows speech process failed: {exc}") from exc
