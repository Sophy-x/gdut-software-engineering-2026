"""为界面逻辑测试提供独立的终端输入输出，不要求物理控制台。"""

import sys

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output.plain_text import PlainTextOutput


class CapturedOutput(PlainTextOutput):
    """刷新时取得当前捕获流，兼容 pytest 在测试阶段间替换 stdout。"""

    def flush(self) -> None:
        self.stdout = sys.stdout
        super().flush()


@pytest.fixture(autouse=True)
def terminal_session():
    """保留文本输出供 pytest 捕获，并隔离每个测试的终端会话。"""

    with create_app_session(input=DummyInput(), output=CapturedOutput(sys.stdout)):
        yield
