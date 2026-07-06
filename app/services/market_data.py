# Market data via yfinance, wrapped for async use.
#
# yfinance is synchronous (requests + pandas under the hood), so every call
# goes through asyncio.to_thread to keep the event loop free. Prices are
# cached in-process with a short TTL -- with 10-50 users and one API worker,
# a dict is plenty and saves Redis as a dependency.

import asyncio
import time
from decimal import Decimal

from app.config import settings

FOUR_DP = Decimal("0.0001")


class PriceUnavailableError(Exception):
    """Raised when the upstream provider has no usable price for a ticker."""


# ticker -> (monotonic timestamp, price)
_price_cache: dict[str, tuple[float, Decimal]] = {}

# GET /stocks/{ticker}/history?period=... -> (yfinance period, candle interval)
HISTORY_PERIODS = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "30m"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "ALL": ("max", "1wk"),
}


def _fetch_price_sync(ticker: str) -> Decimal:
    import yfinance as yf  # lazy: keeps app/test imports fast

    try:
        info = yf.Ticker(ticker).fast_info
        last = info["last_price"]
    except Exception as exc:
        raise PriceUnavailableError(f"No price available for {ticker}") from exc
    if last is None:
        raise PriceUnavailableError(f"No price available for {ticker}")
    return Decimal(str(last)).quantize(FOUR_DP)


def _fetch_quote_sync(ticker: str) -> dict:
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).fast_info
        last = info["last_price"]
    except Exception as exc:
        raise PriceUnavailableError(f"No quote available for {ticker}") from exc
    try:
        # fast_info only aliases snake_case keys through [], not .get()
        prev_close = info["previous_close"]
    except Exception:
        prev_close = None
    if last is None:
        raise PriceUnavailableError(f"No quote available for {ticker}")

    price = Decimal(str(last)).quantize(FOUR_DP)
    quote = {"ticker": ticker, "price": price, "previous_close": None,
             "change": None, "change_pct": None}
    if prev_close:
        prev = Decimal(str(prev_close)).quantize(FOUR_DP)
        quote["previous_close"] = prev
        quote["change"] = price - prev
        quote["change_pct"] = ((price - prev) / prev * 100).quantize(FOUR_DP)
    return quote


def _fetch_history_sync(ticker: str, period: str) -> list[dict]:
    import yfinance as yf

    yf_period, interval = HISTORY_PERIODS[period]
    try:
        df = yf.Ticker(ticker).history(period=yf_period, interval=interval)
    except Exception as exc:
        raise PriceUnavailableError(f"No history available for {ticker}") from exc
    if df is None or df.empty:
        raise PriceUnavailableError(f"No history available for {ticker}")

    return [
        {
            "timestamp": ts.isoformat(),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        }
        for ts, row in df.iterrows()
    ]


async def get_price(ticker: str) -> Decimal:
    """Current price with TTL cache. This is the default `price_getter`
    injected into the order/portfolio services -- tests swap in a fake."""
    ticker = ticker.upper()
    cached = _price_cache.get(ticker)
    now = time.monotonic()
    if cached is not None and now - cached[0] < settings.price_cache_ttl_seconds:
        return cached[1]

    price = await asyncio.to_thread(_fetch_price_sync, ticker)
    _price_cache[ticker] = (time.monotonic(), price)
    return price


async def get_quote(ticker: str) -> dict:
    return await asyncio.to_thread(_fetch_quote_sync, ticker.upper())


async def get_history(ticker: str, period: str) -> list[dict]:
    if period not in HISTORY_PERIODS:
        raise ValueError(f"period must be one of {sorted(HISTORY_PERIODS)}")
    return await asyncio.to_thread(_fetch_history_sync, ticker.upper(), period)
