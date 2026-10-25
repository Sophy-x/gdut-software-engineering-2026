"""通过 Windows 自带的 System.Speech 提供终端语音能力。"""

import asyncio
import base64
import os
import shutil
import subprocess
from pathlib import Path


class VoiceError(RuntimeError):
    """语音设备或 Windows 语音服务不可用时抛出。"""


_RECOGNIZE_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {
    $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $engine.SetInputToDefaultAudioDevice()
    $result = $engine.Recognize([TimeSpan]::FromSeconds(12))
    if ($null -eq $result -or $result.Confidence -lt 0.45) { exit 2 }
    [Console]::WriteLine([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($result.Text)))
} finally {
    $engine.Dispose()
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

    async def recognize(self) -> str | None:
        """监听最多 12 秒并返回识别文本，无有效语音时返回 None。"""

        return await asyncio.to_thread(self._recognize_sync)

    def _recognize_sync(self) -> str | None:
        """执行一次 Windows DictationGrammar 语音识别。"""

        result = _run_powershell(_RECOGNIZE_SCRIPT, timeout=20)
        if result.returncode == 2:
            return None
        if result.returncode != 0:
            detail = result.stderr.strip() or "speech recognition failed"
            raise VoiceError(detail)
        try:
            return base64.b64decode(result.stdout.strip(), validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise VoiceError("Windows speech recognition returned invalid text") from exc


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
