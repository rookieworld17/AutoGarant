from __future__ import annotations

import logging
import time
from decimal import Decimal

import aiohttp

logger = logging.getLogger(__name__)

_CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
_CACHE_TTL = 3600.0
_REQUEST_TIMEOUT = 5.0

_cached_rate: Decimal | None = None
_cached_at: float = 0.0


async def get_usd_rub_rate() -> Decimal | None:
    global _cached_rate, _cached_at

    now = time.monotonic()
    if _cached_rate is not None and now - _cached_at < _CACHE_TTL:
        return _cached_rate

    try:
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as http:
            async with http.get(_CBR_URL) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        rate = Decimal(str(data["Valute"]["USD"]["Value"]))
    except Exception as exc:
        logger.warning("Failed to fetch USD/RUB rate: %s", exc)
        return _cached_rate

    _cached_rate = rate
    _cached_at = now
    return rate
