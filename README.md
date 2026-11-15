# btc-cent-forecast-01 — 4-hour Bitcoin price forecaster

Entry for the make.fun bounty `btc-cent-forecast-01` ($250, 100 paid places).
The program reads one case file (`<id>.in`: 4,320 one-minute BTC closes for
the 72 hours ending at the checkpoint) and writes `<id>.out` with a single
forecast: the expected BTC price 240 minutes after the checkpoint.

## How it forecasts

`guess = last_close * exp(pred)` where

```
pred = -0.05 * r4h - 0.05 * r1h - 0.0008, clipped to +/-0.01
```

`r4h` / `r1h` are the log returns of the last 4 hours / 1 hour.

4h-ahead BTC returns are near-unpredictable noise (lag-1 autocorrelation of
4h returns is about -0.05), so any large directional bet loses to
persistence. What survives out-of-sample validation is a small
mean-reversion tilt (prices slightly fade the last 1–4h move) plus a small
negative drift (the recent regime drifts down). The bet is tiny (at most
~0.5% off the checkpoint close), so the worst case is a small loss versus
persistence while the typical case gains.

Backtested on Yahoo BTC-USD 1-minute closes (Oct 30 – Nov 14 2026),
checkpoints every 4h. MAE in cents versus persistence:

| stretch | improvement |
|---|---|
| tune, Nov 2–9 | -2.14% |
| held-out, Nov 10–14 (incl. Nov 13 crash) | -4.19% |
| recent, Nov 12–14 | -3.46% |
| practice cases (Orca inputs, Yahoo proxy answers) | -2.42% |

## Run it locally

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only, no network, deterministic: two runs
on the same case write identical bytes. A broken or missing input never
crashes the run; the output is always a valid finite price in
(0, 10,000,000).

## License

MIT — see `LICENSE`.
