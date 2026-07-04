# PROMPT PER AGENTE CURSOR — VPS Windows (Contabo)

Copia tutto da qui in giù e incollalo a Cursor. Inserisci il token GitHub dove indicato (NON committarlo mai nel repo: è pubblico).

---

Sei un agente che opera direttamente su una VPS Windows (Contabo) dove girano terminali MetaTrader 5. Devi costruire il backtester Python della strategia **VLR (VWAP Liquidity Reversal)** seguendo la specifica completa già presente nel repo. Lavora in modo sequenziale: un modulo alla volta, testato e validato prima di passare al successivo. Non combinare mai più modifiche in un singolo test. Non fare assunzioni: se un dato manca, fermati e chiedilo.

## STEP 0 — Setup ambiente
```
cd C:\
git clone https://<GITHUB_TOKEN>@github.com/daniele4trading-boop/vlr-strategy.git VLR_Strategy
cd C:\VLR_Strategy
python -m venv venv
venv\Scripts\activate
pip install pandas numpy pyyaml optuna MetaTrader5 pyarrow matplotlib
```
Poi **leggi integralmente** `docs/PROMPT_CURSOR_VLR_Backtest.md`: contiene l'intera specifica dei moduli M0–M8, i parametri con range di ottimizzazione e i criteri di accettazione. Quella specifica è la fonte di verità; questo prompt aggiunge solo le istruzioni operative VPS.

## STEP 1 — Misurazione spread reale (`tools/measure_spreads.py`)
Prima di qualsiasi backtest, misura i costi reali. Crea uno script che:
- Si connette a un terminale MT5 installato via pacchetto `MetaTrader5` (usa `initialize(path=...)`). **REGOLA CRITICA:** i terminali MT5 vanno chiusi manualmente prima di lanciare Python — il pacchetto li apre da solo; lancio simultaneo causa "Authorization failed". Prima di iniziare, chiedi all'utente quale terminale usare e conferma che sia chiuso.
- Campiona `symbol_info_tick()` per i 9 simboli (XAUUSD, EURUSD, GBPUSD, USDJPY, US500, NAS100, GER40, BTCUSD, ETHUSD — verifica i nomi esatti del broker con `symbols_get()`, es. suffissi tipo "US500.cash") ogni 5 secondi per almeno 2 ore in sessione attiva.
- Output: `config/symbols.yaml` con spread medio/mediano/p90 in punti, digits, point, tick_value, più ATR(14) M5 corrente per calcolare `cost_R` stimato. Sostituisce le stime attuali nel file.

## STEP 2 — Download dati storici (`tools/download_data.py`)
- Via `copy_rates_range()`: M1 per i 9 simboli, minimo 24 mesi (di più se il broker li ha).
- Salva in `data/{SYMBOL}_M1.parquet`. Logga per ogni simbolo: barre totali, range date, gap > 5 min.
- I dati NON vanno committati su git (aggiorna `.gitignore` con `data/` e `venv/`).

## STEP 3 — Costruzione moduli M0→M8
Segui la specifica del documento, nell'ordine. Per ogni modulo:
1. Implementa
2. Scrivi un test minimo (dati sintetici o subset reale)
3. Mostra il risultato del test
4. Solo dopo passa al modulo successivo

Default già ottimizzati a livello strutturale (NON cambiarli senza dati): `TP1Pct=0.40`, split TP `30/20/50`, `BEMode=IMMEDIATE`, `BEOffsetATR` da ottimizzare.

## STEP 4 — Primo backtest di validazione
```
python run_backtest.py --symbol XAUUSD --tf M5 --from 2024-07 --to 2026-06
```
Prima di mostrare i risultati esegui il sanity check no-lookahead (shift +1 barra sugli indicatori deve peggiorare i risultati). Poi report completo: expectancy lorda/netta, WR per classe di esito (LOSS / TP1→BE / TP2 / FULL), trade/mese, MaxDD, log dei setup scartati con motivo (serve a misurare la selettività reale dei filtri). **Check critico: P(loss) deve essere < 42% (break-even strutturale XAUUSD): se superiore, flag rosso e stop per analisi.**

## STEP 5 — Estensione multi-simbolo + ottimizzazione
- Backtest sugli altri 8 simboli con gli stessi default (nessuna riottimizzazione per-simbolo in questa fase).
- Solo dopo: M8 con Optuna (300 trial, obiettivo expectancy netta OOS su walk-forward 6+2 mesi, selezione a plateau).
- Per BTC/ETH riporta sempre lordo vs netto separati.

## STEP 6 — Commit e push
Commit atomici per modulo con messaggi chiari (`git push` con il token). Mai committare: token, dati storici, venv.

## Regole permanenti
- Nessuna assunzione: solo dati verificati (codice letto, log, output reali)
- Un solo cambiamento per iterazione di test
- Ogni default leggibile da `config/strategy.yaml`, zero valori hardcoded
- Se un risultato sembra troppo bello (PF > 3, WR > 80%), sospetta lookahead o bug prima di festeggiare
