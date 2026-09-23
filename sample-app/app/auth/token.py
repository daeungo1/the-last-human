"""액세스 토큰 갱신."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, replace

from ..http_client import HttpError, Transport, post_json

#: 만료 판정 시 앞당겨 잡는 여유. 시계 오차와 왕복 시간을 흡수한다.
CLOCK_SKEW_SEC = 60.0

#: 일시적 실패에 대해 시도할 최대 횟수.
MAX_RETRIES = 3

#: 지수 백오프의 기준 간격(초).
BASE_BACKOFF_SEC = 0.2

TOKEN_ENDPOINT = os.environ.get("ORDERLY_TOKEN_ENDPOINT", "https://auth.internal/oauth/token")


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: float


def is_expired(token: TokenSet, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return now >= token.expires_at - CLOCK_SKEW_SEC


def backoff_for(attempt: int) -> float:
    """시도 횟수에 대한 백오프 간격을 계산한다."""
    return BASE_BACKOFF_SEC * (2**attempt)


async def refresh(transport: Transport, token: TokenSet) -> TokenSet:
    """리프레시 토큰으로 새 토큰 세트를 받아온다.

    일시적 실패는 흡수하고, 영구 실패는 그대로 던진다.
    """
    try:
        body = await post_json(
            transport,
            TOKEN_ENDPOINT,
            {"grant_type": "refresh_token", "refresh_token": token.refresh_token},
        )
        return TokenSet(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token", token.refresh_token),
            expires_at=time.time() + body["expires_in"],
        )
    except HttpError as err:
        if err.transient:
            return token
        raise


async def ensure_fresh(transport: Transport, token: TokenSet) -> TokenSet:
    """만료가 임박했으면 갱신하고, 아니면 그대로 돌려준다."""
    if not is_expired(token):
        return token
    return await refresh(transport, token)
