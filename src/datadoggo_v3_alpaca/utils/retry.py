"""Alpaca API呼び出し時のリトライロジック."""

from __future__ import annotations

import time
from typing import Any, Callable

from alpaca.common.exceptions import APIError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from datadoggo_v3_alpaca.utils.logger import get_logger

logger = get_logger(__name__)


def is_rate_limit_error(exception: BaseException) -> bool:
    """
    APIErrorが429（レート制限）エラーかどうかを判定する.

    Parameters
    ----------
    exception : BaseException
        判定対象の例外

    Returns
    -------
    bool
        429エラーの場合True
    """
    # APIErrorまたはstatus_code属性を持つ例外が429の場合にTrue
    if isinstance(exception, APIError):
        return hasattr(exception, "status_code") and exception.status_code == 429  # type: ignore[attr-defined]
    # テスト用: status_code属性を持つ例外も判定可能
    if hasattr(exception, "status_code"):
        return exception.status_code == 429  # type: ignore[attr-defined]
    return False


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """
    リトライ実行時にログを出力する.

    Parameters
    ----------
    retry_state : RetryCallState
        Tenacityのリトライ状態
    """
    attempt_number = retry_state.attempt_number
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        wait_time = getattr(retry_state.next_action, "sleep", 0) if retry_state.next_action else 0

        logger.warning(
            "alpaca_api_rate_limited",
            attempt=attempt_number,
            wait_time_seconds=round(wait_time, 2),
            exception=str(exception),
        )


# Alpaca APIレート制限対応のリトライデコレータ
# - Alpacaのレート制限: 200リクエスト/分
# - 戦略: Exponential Backoff + Jitter（ランダム性）
# - 待機時間: 1秒〜60秒（60秒待てば確実にリセット）
# - 最大リトライ: 5回（合計約2分の待機時間）
alpaca_retry = retry(
    retry=retry_if_exception(is_rate_limit_error),
    wait=wait_random_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    before_sleep=log_retry_attempt,
    reraise=True,
)


def alpaca_retry_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    非同期関数用のAlpaca APIリトライデコレータ.

    通常のalpaca_retryは同期関数用のため、非同期関数には使用できない。
    この関数は非同期関数をラップして、同じリトライロジックを適用する。

    Parameters
    ----------
    func : Callable
        ラップする非同期関数

    Returns
    -------
    Callable
        リトライ機能を持つ非同期関数
    """
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        max_attempts = 5
        min_wait = 1
        max_wait = 60
        multiplier = 1

        for attempt in range(1, max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except APIError as e:
                if not is_rate_limit_error(e):
                    raise

                if attempt >= max_attempts:
                    logger.error(
                        "alpaca_api_rate_limit_max_retries_exceeded",
                        max_attempts=max_attempts,
                    )
                    raise

                # Exponential backoff with jitter
                wait_time = min(max_wait, min_wait * (2 ** (attempt - 1)) * multiplier)
                # Add jitter (±20%)
                import random
                jitter = random.uniform(0.8, 1.2)
                actual_wait = wait_time * jitter

                logger.warning(
                    "alpaca_api_rate_limited",
                    attempt=attempt,
                    wait_time_seconds=round(actual_wait, 2),
                    exception=str(e),
                )

                time.sleep(actual_wait)

        raise RuntimeError("Unreachable code")  # pragma: no cover

    return wrapper
