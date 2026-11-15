#!/usr/bin/env python3
"""btc-cent-forecast-01 entry: 4-hour Bitcoin price forecaster.

Reads every <id>.in in MAKEFUN_INPUT_DIR (default /input): one market,
4,320 one-minute BTC closes for the 72 hours ending at the checkpoint.
Writes <id>.out to MAKEFUN_OUTPUT_DIR (default /output):
{"forecasts": [{"case": "<id>", "price": <number>}]}

Model (backtested on Yahoo BTC-USD 1-minute closes, Oct 30 - Nov 14 2026,
checkpoints every 4h; tuned Nov 2-9, validated held-out Nov 10-14):
  guess = last_close * exp(pred), where
  pred = -0.05 * r4h - 0.05 * r1h - 0.0008, clipped to +/-0.01.
  r4h / r1h are the log returns of the last 4 hours / 1 hour.

Why: 4h-ahead BTC returns are near-unpredictable noise (lag-1 autocorr of
4h returns ~ -0.05), so any big directional bet loses to persistence.
What survives out-of-sample is a small mean-reversion tilt (prices
slightly fade the last 1-4h move) plus a small negative drift (the
recent regime drifts down). The bet is tiny (at most ~0.5% off the
checkpoint close), so the worst case is a small loss vs persistence
while the typical case gains ~2-3% MAE. Measured MAE in cents vs
persistence: tune -2.14%, held-out -4.19%, recent (Nov 12-14) -3.46%,
practice cases (Orca inputs, Yahoo proxy answers) -2.42%.

Standard library only, no network, deterministic: the same input
always writes the same bytes. A broken or missing input never crashes
the run: the output is always a valid finite price in (0, 10,000,000).
"""

import json
import math
import os
import sys

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999

# Backtested weights (see module docstring). Small on purpose: the
# 4h-ahead signal is weak, so the forecast stays close to persistence.
W_R4H = -0.05
W_R1H = -0.05
DRIFT = -0.0008
CLIP = 0.01


def price5(x):
    """Keep x on the 5-decimal grid inside (0, 10,000,000)."""
    if not (isinstance(x, (int, float)) and math.isfinite(x)):
        x = 60000.0
    x = min(MAX_PRICE, max(MIN_PRICE, x))
    return round(x, 5)


def forecast(prices):
    """Forecast the close 240 minutes after the last price in `prices`."""
    finite = [p for p in prices if isinstance(p, (int, float)) and math.isfinite(p) and p > 0]
    if not finite:
        return price5(60000.0)
    last = finite[-1]
    logs = [math.log(p) for p in finite]
    n = len(logs)
    pred = DRIFT
    if n > 240:
        pred += W_R4H * (logs[-1] - logs[-241])
    elif n > 1:
        # Short window: use the whole available return, same spirit.
        pred += W_R4H * (logs[-1] - logs[0])
    if n > 60:
        pred += W_R1H * (logs[-1] - logs[-61])
    pred = max(-CLIP, min(CLIP, pred))
    return price5(last * math.exp(pred))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        names = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    except FileNotFoundError:
        names = []
    for name in names:
        case_id = name[:-3]
        guess = None
        try:
            with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as fh:
                case = json.load(fh)
            markets = case.get("markets") or []
            prices = markets[0].get("prices") if markets else None
            if not isinstance(prices, list):
                # Tolerate a flat case that carries prices at the top level.
                top = case.get("prices")
                prices = top if isinstance(top, list) else None
            if isinstance(prices, list) and prices:
                guess = forecast(prices)
        except Exception:
            guess = None
        if guess is None:
            guess = price5(60000.0)
        out = {"forecasts": [{"case": case_id, "price": guess}]}
        with open(os.path.join(OUTPUT_DIR, case_id + ".out"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
