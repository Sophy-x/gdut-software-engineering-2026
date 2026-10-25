"""通过 Windows 自带的 System.Speech 提供终端语音能力。"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
from pathlib import Path


class VoiceError(RuntimeError):
    """语音设备或 Windows 语音服务不可用时抛出。"""


class NoSpeechDetected(VoiceError):
    """监听窗口内没有检测到语音。"""


class LowConfidenceSpeech(VoiceError):
    """检测到语音，但识别置信度过低。"""

    def __init__(self, transcript: str, confidence: float) -> None:
        self.transcript = transcript
        self.confidence = confidence
        super().__init__(
            f"Speech was detected but recognition confidence was too low "
            f"({confidence:.2f})"
        )


_RECOGNIZE_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {
    $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $engine.SetInputToDefaultAudioDevice()
    $result = $engine.Recognize([TimeSpan]::FromSeconds(12))
    if ($null -eq $result) { exit 2 }
    $payload = @{
        text = $result.Text
        confidence = [double]$result.Confidence
    } | ConvertTo-Json -Compress
    [Console]::WriteLine([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload)))
} finally {
    $engine.Dispose()
}
"""

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


class WindowsSpeech:
    """封装 Windows PowerShell 的离线语音识别和合成 API。"""

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

    async def recognize(self) -> str:
        """监听最多 12 秒并返回识别文本，无语音或设备异常时抛出 VoiceError。"""

        return await asyncio.to_thread(self._recognize_sync)

    async def speak(self, text: str) -> None:
        """使用 Windows 默认语音合成器朗读文本。"""

        if not text.strip():
            return
        await asyncio.to_thread(self._speak_sync, text)

    def _recognize_sync(self) -> str:
        """执行一次 Windows DictationGrammar 语音识别并校验识别结果。"""

        result = _run_powershell(_RECOGNIZE_SCRIPT, timeout=20)
        if result.returncode == 2:
            raise NoSpeechDetected("No speech detected within 12 seconds")
        if result.returncode == 3:
            raise LowConfidenceSpeech(
                "Speech was detected but recognition confidence was too low"
            )
        if result.returncode != 0:
            detail = result.stderr.strip() or "speech recognition failed"
            raise VoiceError(detail)
        try:
            payload = json.loads(
                base64.b64decode(result.stdout.strip(), validate=True).decode("utf-8")
            )
            transcript = payload["text"]
            confidence = float(payload["confidence"])
            if not isinstance(transcript, str) or not transcript.strip():
                raise ValueError("empty transcript")
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VoiceError("Windows speech recognition returned invalid text") from exc
        if confidence < 0.45:
            raise LowConfidenceSpeech(transcript, confidence)
        return transcript

    def _speak_sync(self, text: str) -> None:
        """执行一次 Windows 语音合成。"""

        encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
        result = _run_powershell(
            _SYNTHESIZE_SCRIPT.replace("__TEXT__", encoded_text), timeout=120
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
