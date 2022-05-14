from logging import DEBUG
from perscache._logger import MAX_LEN, debug, trace, _trim
import pytest


@pytest.fixture
def mock_handler():
    class MockHandler:
        def __init__(self):
            self.messages = []
            self.level = DEBUG

        def handle(self, record):
            self.messages.append(record.getMessage())

    handler = MockHandler()
    logger = debug.__self__
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


def test_debug(mock_handler):
    debug("foo")
    assert mock_handler.messages == ["foo"]


def test_trace(mock_handler):
    @trace
    def foo(bar):
        return bar

    foo(1)
    assert mock_handler.messages == [
        "Entering foo, args=(1,), kwargs={}",
        "Exiting foo, result=1",
    ]


def test_trim(mock_handler):
    assert len(_trim("foo" * MAX_LEN)) <= MAX_LEN + 3
