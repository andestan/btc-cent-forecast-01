# btc-cent-forecast-01 entry: damped-EMA level forecast.
#
# Model (chosen by backtest, see NOTES.md):
#   forecast = 0.75 * last_close + 0.25 * EMA_180(last 72h of 1-minute closes)
# where EMA_180 is the exponential moving average with span 180 minutes
# (alpha = 2 / 181), computed over the case's 4,320 closes.
#
# Why this, and not persistence or trend extrapolation:
# - The house baseline (persistence: guess = last close) is the bar to beat.
# - 4-hour-ahead BTC is close to a random walk: extrapolating the recent
#   trend (OLS slope over 6/12/24h, AR(1) on 4h returns, median 4h return)
#   made the error WORSE in backtest on 139 checkpoints (Oct 23-Nov 15,
#   OKX BTC-USDT 1m): trend models were +3% to +55% worse than persistence.
# - The checkpoint close itself carries microstructure noise (the price is
#   one Orca pool's mid-price; a large trade moves it for a moment), while
#   the target is another single minute's close. Blending the last close
#   75/25 with a 180-minute EMA removes part of that noise without lagging
#   far behind in a trend. A full EMA forecast lags badly (+13.6% worse);
#   the 25% blend was the sweet spot.
# - Backtest (MAE in cents, lower is better; persistence = 100%):
#     OKX 139 checkpoints Oct 23-Nov 15:  this model -1.37% vs persistence
#     OKX crash-regime split Nov 9-15:    this model -1.54% vs persistence
#     kit practice series, hourly Nov 10:  this model -4.29% vs persistence
#     official 6 practice cases:           this model +2.31% vs persistence
#       (n=6, one $767-move case dominates; not trusted over the n=139 set)
#   The edge is small (~1-1.5% on the large sample) and not statistically
#   proven; it beat persistence on every out-of-sample split, which is the
#   best robustness signal available. The final is 12 cases, so luck will
#   dominate; this is the best-justified forecast, not a guaranteed win.
#
# Contract (from the kit's RULES.txt):
# - Reads every *.in file in $MAKEFUN_INPUT_DIR (else /input), in name order.
# - Each .in is UTF-8 JSON: {"schema": "makefun/btc-cent-case/v1",
#   "competition", "case", "at", "horizon_minutes": 240,
#   "markets": [{"id": "btc-usdc", "name", "start",
#                "prices": [4320 one-minute closes, last = checkpoint close]}]}.
# - Writes /output/<id>.out (or $MAKEFUN_OUTPUT_DIR): exactly
#   {"forecasts": [{"case": "<id>", "price": <number>}]}, price finite,
#   0 < price < 10,000,000, rounded to the grid's 5 decimals.
# - Standard library only, no network, no randomness, no wall-clock use:
#   two runs on the same case write byte-identical output.
# - Fast: one O(n) pass over 4,320 prices, far inside the 8 s/case cap.
#
# Run locally (from the kit directory, or anywhere with the env vars set):
#   mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999
EMA_SPAN_MINUTES = 180
EMA_WEIGHT = 0.25  # forecast = (1 - w) * last + w * EMA_180


def clamp5(x):
    """Keep a price on the grid's 5 decimals and inside (0, 10_000_000)."""
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def ema_last(prices, span):
    """EMA over the whole series, returning only its final value.

    Seeded with the first price; after 4,320 steps the seed's weight is
    (1 - alpha) ** 4319, effectively zero, so the result depends only on
    the recent history, deterministically.
    """
    alpha = 2.0 / (span + 1)
    value = prices[0]
    for price in prices[1:]:
        value = alpha * price + (1.0 - alpha) * value
    return value


def forecast(prices):
    """Forecast the close 240 minutes after the checkpoint."""
    last = prices[-1]
    level = ema_last(prices, EMA_SPAN_MINUTES)
    return (1.0 - EMA_WEIGHT) * last + EMA_WEIGHT * level


def salvage_last_number(obj):
    """Best-effort last price from a partly readable case, else None."""
    try:
        markets = obj["markets"]
        prices = markets[0]["prices"]
        for value in reversed(prices):
            if isinstance(value, (int, float)) and math.isfinite(value):
                return float(value)
    except (KeyError, IndexError, TypeError):
        return None
    return None


def main():
    input_dir = Path(INPUT_DIR)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = sorted(p for p in input_dir.iterdir() if p.name.endswith(".in")) \
        if input_dir.is_dir() else []

    for in_path in inputs:
        case_id = in_path.name[: -len(".in")]
        out_path = output_dir / (case_id + ".out")
        try:
            case = json.loads(in_path.read_text(encoding="utf-8"))
            prices = case["markets"][0]["prices"]
            if not isinstance(prices, list) or not prices:
                raise ValueError("no prices")
            clean = []
            for value in prices:
                number = float(value)
                if not math.isfinite(number) or number <= 0:
                    raise ValueError("bad price")
                clean.append(number)
            price = clamp5(forecast(clean))
        except Exception:
            # Never leave a parseable case without an output: an invalid
            # case is scored as the checkpoint close AND forfeits prizes.
            # Fall back to the checkpoint close (the persistence baseline)
            # when it can be recovered from the file at all.
            try:
                case = json.loads(in_path.read_text(encoding="utf-8"))
                last = salvage_last_number(case)
            except Exception:
                last = None
            if last is None:
                continue
            price = clamp5(last)
        payload = {"forecasts": [{"case": case_id, "price": price}]}
        out_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
