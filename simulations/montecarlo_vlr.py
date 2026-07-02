"""
Monte Carlo VLR multi-simbolo.
ATTENZIONE: simulazione statistica, NON backtest su dati reali.
I costi (cost_R = frazione di R persa per trade in spread+slippage) sono STIME
da verificare misurando spread reale su MT5 demo prima di validare.
Payoff struttura 50/30/20: LOSS=-1R | TP1->BE=+0.375R | TP2+trail=+0.925R | FULL=+1.425R
Scenario base = filtri stretti: p=[0.35, 0.20, 0.30, 0.15]
"""
import numpy as np
np.random.seed(42)

PAYOFF = np.array([-1.0, 0.375, 0.925, 1.425])
P_BASE  = np.array([0.35, 0.20, 0.30, 0.15])

# tpm = trade/mese stimati (sessione; cripto 24/7 -> piu' trade)
# cost_R = costo round-trip in frazione di R (spread+slippage / distanza SL ~1 ATR M5) - STIME
SYMBOLS = {
    # symbol      tpm  cost_R  note
    "XAUUSD":   ( 8,  0.08, "riferimento"),
    "EURUSD":   ( 6,  0.10, "ATR basso, spread pesa"),
    "GBPUSD":   ( 7,  0.10, ""),
    "USDJPY":   ( 6,  0.11, ""),
    "US500":    ( 7,  0.10, "sessione USA"),
    "NAS100":   ( 9,  0.08, "volatile, buon rapporto ATR/spread"),
    "GER40":    ( 6,  0.08, "sessione EU"),
    "BTCUSD":   (14,  0.15, "24/7, spread alto"),
    "ETHUSD":   (13,  0.17, "24/7, spread piu' alto"),
}

N_SIM, MONTHS = 10000, 12
rows = []
print(f"{'Simbolo':<9}{'Tr/mese':>8}{'CostR':>7}{'Exp netta':>11}{'R/anno':>8}{'MaxDD':>7}{'P(anno<0)':>10}{'CI95 R/anno':>16}")
for sym,(tpm,cost,note) in SYMBOLS.items():
    pay = PAYOFF - cost                      # costo su ogni trade, anche vincenti
    exp = (P_BASE*pay).sum()
    n = tpm*MONTHS
    idx = np.random.choice(4, size=(N_SIM,n), p=P_BASE)
    pnl = pay[idx]; eq = pnl.cumsum(axis=1)
    annual = eq[:,-1]
    dd = (np.maximum.accumulate(eq,axis=1)-eq).max(axis=1)
    lo,hi = np.percentile(annual,[2.5,97.5])
    print(f"{sym:<9}{tpm:>8}{cost:>7.2f}{exp:>10.3f}R{np.median(annual):>7.1f}R{np.median(dd):>6.1f}R{(annual<0).mean():>9.1%}{f'[{lo:.0f},{hi:.0f}]':>16}")
    rows.append((sym, exp*tpm*12))

# Portafoglio aggregato (indipendenza assunta - in realta' correlazione riduce diversificazione)
tot = sum(r[1] for r in rows)
print(f"\nPortafoglio 9 simboli (assunzione indipendenza): ~{tot:.0f}R/anno atteso")
print(f"Con 0.25% rischio/trade (prudente su portafoglio): ~{tot*0.25:+.0f}% annuo lineare")
print("\nBreak-even P(loss) per simbolo (con costi):")
for sym,(tpm,cost,note) in SYMBOLS.items():
    pay = PAYOFF - cost
    wr = P_BASE[1:]/P_BASE[1:].sum()
    for pl in np.arange(0.30,0.71,0.01):
        p = np.concatenate([[pl],(1-pl)*wr])
        if (p*pay).sum() < 0:
            print(f"  {sym:<9} P(loss) max {pl-0.01:.0%}"); break
