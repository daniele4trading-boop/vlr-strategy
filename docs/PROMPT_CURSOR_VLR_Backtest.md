# PROMPT CURSOR — Backtester Python "VLR" (VWAP Liquidity Reversal)

Repo: `daniele4trading-boop/vlr-strategy` — Cartella: `backtest/`

---

Costruisci un sistema di backtesting Python completo per la strategia **VLR (VWAP Liquidity Reversal)**: mean reversion verso il VWAP innescata da caccia di liquidità (sweep) confermata da V-Formation. Il sistema deve essere **multi-simbolo**: XAUUSD, forex major (EURUSD, GBPUSD, USDJPY), indici (US500, NAS100, GER40), cripto (BTCUSD, ETHUSD).

**REGOLA FONDAMENTALE — NORMALIZZAZIONE:** nessun parametro in punti assoluti. Tutte le soglie di prezzo sono espresse in **multipli di ATR(14)** del timeframe operativo, così la stessa configurazione è trasferibile tra simboli. Le uniche eccezioni sono i costi (spread/commissioni), definiti per simbolo nel config.

## Architettura (moduli separati)

```
vlr_backtest/
├── config/
│   ├── symbols.yaml          # config per simbolo
│   └── strategy.yaml         # parametri strategia (default + range ottimizzazione)
├── m0_data_loader.py         # caricamento CSV/MT5, validazione dati, gap check
├── m1_indicators.py          # VWAP sessione + bande σ, ATR, livelli liquidità
├── m2_setup_detector.py      # estensione + sweep + V-Formation
├── m3_trigger.py             # trigger A / trigger B
├── m4_trade_manager.py       # entry, SL, TP1/TP2/TP3, BE, trailing
├── m5_costs.py               # spread, commissioni, slippage per simbolo
├── m6_backtest_engine.py     # loop event-driven bar-by-bar, no lookahead
├── m7_metrics.py             # expectancy R, PF, WR, MaxDD, MC bootstrap
├── m8_optimizer.py           # grid/random search con walk-forward
└── run_backtest.py           # entry point CLI
```

## M0 — Dati
- Input: CSV OHLCV M1 (o export MT5). Resample interno a M5 (timeframe operativo default, parametro `TF_OP`).
- Validazione: gap > 5 minuti loggati; barre con volume 0 in sessione flaggate; nessuna interpolazione silenziosa.
- **Volume:** forex/indici/oro CFD = tick volume (dichiararlo nel report). Cripto = volume reale se disponibile.

## M1 — Indicatori
- **VWAP di sessione** con reset configurabile per simbolo (`vwap_reset`): forex/oro/indici = 00:00 broker; cripto = 00:00 UTC (mercato 24/7). Bande a ±1σ e ±2σ calcolate come deviazione standard volume-pesata dal VWAP.
- **ATR(14)** su TF operativo.
- **Livelli liquidità:** PDH/PDL, high/low sessione Asia (per cripto: high/low delle ultime 8 ore come proxy), equal highs/lows = 2+ estremi entro `EqToleranceATR × ATR` negli ultimi `EqLookback` barre.

## M2 — Setup (short; long speculare)
Tutte e 4 le condizioni sulla stessa barra o entro `SetupWindowBars`:
1. **Estensione:** prezzo oltre banda VWAP + `KDev`·σ
2. **Sweep:** high supera livello liquidità di ≥ `SweepMinATR × ATR` ma chiusura sotto il livello
3. **V-Formation:** impulso rialzista ≥ `VImpulseATR × ATR` in ≤ `VMaxBars` barre, poi ritorno ≥ `VRetracePct` dell'impulso in ≤ `VMaxBars` barre
4. **Sessione:** dentro `session_start`–`session_end` (per simbolo; cripto = 24/7 ma con flag `crypto_avoid_weekend` testabile)

## M3 — Trigger (parametro `TriggerMode`: A / B / BOTH per confronto)
- **A:** chiusura TF operativo sotto livello sweepato E sotto low della candela di sweep
- **B:** break del pivot della V con candela displacement body ≥ `DispMinATR × ATR`
- Entry: sell stop 0.05×ATR sotto la candela trigger, scadenza `OrderExpiryBars`

## M4 — Gestione trade
- **SL** = estremo sweep + `BufferATR × ATR`. Skip se SL totale > `SLMaxATR × ATR`.
- **TP1** = `TP1Pct` della distanza entry→VWAP → chiude `TP1Size`% 
- **TP2** = VWAP → chiude `TP2Size`%
- **TP3** = banda opposta −1σ (o liquidità opposta se più vicina) → runner con trailing `TrailMult × ATR` aggiornato a chiusura barra
- **⚡ NUOVI PARAMETRI (ottimizzazione anti-selettività):**
  - `TP1Pct`: default 0.50, range **0.40–0.70** (spostare TP1 più lontano aumenta il payoff medio)
  - `BEOffsetATR`: default 0.0, range **0.0–0.5** — il BE dopo TP1 non va a entry secco ma a entry ± offset (ritardare il BE riduce i troncamenti a +0.375R)
  - `BEMode`: `IMMEDIATE` (BE subito a TP1) / `DELAYED` (BE solo dopo che il prezzo ha percorso `BEDelayPct` della distanza TP1→TP2, range 0.2–0.5)
- Filtri opzionali on/off: `MinRRDist` (default 1.5), max 1 trade per livello/sessione, filtro ATR min/max, filtro news (skip ±30 min da orari in `news_blackout.csv` se fornito).

## M5 — Costi (per simbolo, da symbols.yaml)
```yaml
XAUUSD:  {spread_pt: 20,  commission_lot: 7,  slippage_atr: 0.02}
EURUSD:  {spread_pt: 1,   commission_lot: 7,  slippage_atr: 0.01}
BTCUSD:  {spread_pt: 2500, commission_lot: 0, slippage_atr: 0.05}
ETHUSD:  {spread_pt: 180, commission_lot: 0,  slippage_atr: 0.05}
# ... compilare tutti; valori da misurare sul broker reale prima del test
```
**I costi cripto vanno misurati sul broker reale (MT5 demo) prima di validare i risultati** — lo spread alto può uccidere l'edge su BTC/ETH: il report deve mostrare expectancy lorda E netta per evidenziarlo.

## M6 — Engine
- Event-driven bar-by-bar M1 (esecuzione intra-bar su dati M1 anche se segnali su M5). **Zero lookahead:** ogni indicatore usa solo barre chiuse.
- Regola conservativa: se nella stessa barra M1 vengono toccati sia SL che TP → conta SL.

## M7 — Metriche (per simbolo + aggregato portafoglio)
- Expectancy in R (lorda/netta), Profit Factor, WR per classe di esito (LOSS / TP1→BE / TP2 / FULL), trade/mese, MaxDD in R e %, Sharpe su rendimenti mensili.
- **Bootstrap Monte Carlo** (10.000 reshuffle) su distribuzione trade → CI 95% su expectancy e MaxDD.
- Verifica di coerenza col modello teorico: P(loss) deve restare < 44% (break-even strutturale calcolato) — se un simbolo supera il 44%, flag rosso nel report.

## M8 — Ottimizzazione
- Walk-forward: 6 mesi in-sample / 2 mesi out-of-sample, rolling.
- Parametri e range: `KDev` 1.5–2.5 (step 0.25), `SweepMinATR` 0.1–0.5, `VRetracePct` 0.50–0.80, `VMaxBars` 5–12, `BufferATR` 0.1–0.4, `SLMaxATR` 1.0–2.0, `TrailMult` 0.5–1.5, `TP1Pct` 0.40–0.70, `BEOffsetATR` 0.0–0.5, `BEMode` + `BEDelayPct` 0.2–0.5, `TriggerMode` A/B.
- Criterio di selezione: expectancy netta OOS, penalizzata se n. trade OOS < 30 (statisticamente insufficiente).
- Output: tabella parametri per simbolo + set "robusto" unico (parametri che funzionano su ≥ 70% dei simboli senza riottimizzazione).

## Criteri di accettazione
1. `python run_backtest.py --symbol XAUUSD --tf M5 --from 2024-01 --to 2026-06` produce report completo senza errori
2. Test no-lookahead: shift artificiale di +1 barra sugli indicatori deve peggiorare i risultati (sanity check)
3. Report confronto lordo vs netto per BTCUSD/ETHUSD
4. Log di ogni trade: timestamp, esito classe, R, motivo skip per i setup scartati (per misurare la selettività reale dei filtri)
5. Nessuna assunzione non dichiarata: ogni default deve essere leggibile da strategy.yaml
