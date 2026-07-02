# VLR — VWAP Liquidity Reversal

Strategia mean-reversion multi-simbolo: caccia di liquidità (sweep) + V-Formation come conferma + VWAP come target statistico.

## Struttura
- `docs/PROMPT_CURSOR_VLR_Backtest.md` — specifica completa del backtester Python (moduli M0–M8, parametri, criteri di accettazione)
- `simulations/montecarlo_vlr.py` — Monte Carlo multi-simbolo (10.000 run × 12 mesi)
- `backtest/` — (da generare con Cursor dal prompt)

## Simboli target
XAUUSD, EURUSD, GBPUSD, USDJPY, US500, NAS100, GER40, BTCUSD, ETHUSD

## ⚠️ Nota metodologica
Le simulazioni Monte Carlo usano probabilità di esito **ipotizzate** e costi **stimati**. Non sostituiscono il backtest su dati reali. I costi (spread/slippage) vanno misurati su MT5 demo del broker reale prima di validare qualsiasi risultato, in particolare per BTC/ETH.

Struttura TP: 50/30/20 — TP1 porta a BE, TP2 = VWAP, runner con trailing ATR.
Break-even strutturale: P(loss) ≤ 37–42% a seconda dei costi del simbolo.
