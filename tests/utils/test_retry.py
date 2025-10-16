"""retryロジックの振る舞いを検証するテスト群."""

import pytest

from datadoggo_v3_alpaca.utils.retry import alpaca_retry, is_rate_limit_error


class DummyAPIError(Exception):
    """テスト用のAPIError実装（status_codeを持つ）."""

    def __init__(self, status_code: int, message: str = "Test error") -> None:
        super().__init__(message)
        self._status_code = status_code

    @property
    def status_code(self) -> int:
        return self._status_code


def test_is_rate_limit_error_returns_true_for_429() -> None:
    """
    正常系: 429エラーの場合、is_rate_limit_errorがTrueを返すことを確認する.

    検証観点:
    - status_code=429の場合にTrueが返される
    """
    error = DummyAPIError(status_code=429, message="Rate limit exceeded")
    assert is_rate_limit_error(error) is True


def test_is_rate_limit_error_returns_false_for_non_429() -> None:
    """
    正常系: 429以外のエラーの場合、is_rate_limit_errorがFalseを返すことを確認する.

    検証観点:
    - status_code=500の場合にFalseが返される
    - status_code=404の場合にFalseが返される
    """
    error_500 = DummyAPIError(status_code=500, message="Server error")
    assert is_rate_limit_error(error_500) is False

    error_404 = DummyAPIError(status_code=404, message="Not found")
    assert is_rate_limit_error(error_404) is False


def test_is_rate_limit_error_returns_false_for_non_api_error() -> None:
    """
    正常系: APIError以外の例外の場合、is_rate_limit_errorがFalseを返すことを確認する.

    検証観点:
    - ValueErrorなど他の例外はFalseが返される
    """
    error = ValueError("Some value error")
    assert is_rate_limit_error(error) is False


def test_alpaca_retry_succeeds_on_first_attempt() -> None:
    """
    正常系: エラーが発生しない場合、リトライせずに成功することを確認する.

    検証観点:
    - デコレータを適用した関数が正常に実行される
    - 戻り値が正しく返される
    """
    call_count = [0]

    @alpaca_retry
    def successful_function() -> str:
        call_count[0] += 1
        return "success"

    result = successful_function()
    assert result == "success"
    assert call_count[0] == 1  # 1回のみ呼ばれる


def test_alpaca_retry_retries_on_429_error() -> None:
    """
    正常系: 429エラーが発生した場合、リトライ後に成功することを確認する.

    検証観点:
    - 429エラーが発生した場合にリトライされる
    - 2回目で成功した場合、合計2回呼ばれる
    """
    call_count = [0]

    @alpaca_retry
    def function_with_retry() -> str:
        call_count[0] += 1
        if call_count[0] == 1:
            raise DummyAPIError(status_code=429, message="Rate limit")
        return "success after retry"

    result = function_with_retry()
    assert result == "success after retry"
    assert call_count[0] == 2  # 1回目失敗、2回目成功


def test_alpaca_retry_does_not_retry_on_non_429_error() -> None:
    """
    正常系: 429以外のエラーの場合、リトライせずに即座に例外を投げることを確認する.

    検証観点:
    - 500エラーなど429以外のエラーはリトライされない
    - 1回のみ呼ばれて例外が発生する
    """
    call_count = [0]

    @alpaca_retry
    def function_with_500_error() -> str:
        call_count[0] += 1
        raise DummyAPIError(status_code=500, message="Server error")

    with pytest.raises(Exception) as exc_info:
        function_with_500_error()

    assert isinstance(exc_info.value, DummyAPIError)
    assert exc_info.value.status_code == 500
    assert call_count[0] == 1  # リトライされない


def test_alpaca_retry_raises_after_max_attempts() -> None:
    """
    異常系: 最大リトライ回数を超えた場合、例外が発生することを確認する.

    検証観点:
    - 最大5回の試行（初回含む）で失敗する場合、最終的に例外が発生する
    - 合計5回呼ばれる（stop_after_attempt(5)の仕様）
    """
    call_count = [0]

    @alpaca_retry
    def always_fails() -> str:
        call_count[0] += 1
        raise DummyAPIError(status_code=429, message="Always rate limited")

    with pytest.raises(Exception):
        always_fails()

    assert call_count[0] == 5  # stop_after_attempt(5)なので5回試行
