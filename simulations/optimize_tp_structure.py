"""
Ottimizzazione strutturale TP della strategia VLR.
Modello: P(prezzo raggiunge distanza d prima dello stop) = S(d) = exp(-lam*d)
Calibrazione su scenario base: S(0.75R)=0.65 -> lam=0.574
(verifica: S(1.5R)=0.42 vs 0.45 assunto; S(3R)=0.18 vs 0.15 assunto - coerente)
NOTA: modello semplificato, serve a ordinare le strutture TP tra loro,
non a predire rendimenti assoluti. Validazione finale su dati reali.
LIMITE NOTO: il modello NON prezza il costo di uno stop piu' stretto (BE offset
positivo): i risultati con BE+ sono ottimisti. Conclusione robusta = split 30/20/50
con TP1 al 40%; BE offset da determinare SOLO su dati reali.
"""
import numpy as np
from itertools import product

LAM = -np.log(0.65)/0.75      # 0.574
D_VWAP = 1.5                   # distanza entry->VWAP in R (caso MinRRDist=1.5)
COST = 0.08                    # costo XAUUSD di riferimento
S = lambda d: np.exp(-LAM*d)

def expectancy(tp1pct, s1, s2, be_offset, be_mode, be_delay=0.35, trail_give=1.0):
    s3 = 1-s1-s2
    d1, d2 = tp1pct*D_VWAP, D_VWAP
    S1, S2 = S(d1), S(d2)
    p_reach2 = S2/S1                       # P(d2 | d1)
    runner_exit = d2 + 1/LAM - trail_give  # uscita attesa runner (memoryless - giveback trailing)
    p_full = 0.5                           # quota dei runner che estendono oltre d2 (conserv.)

    E = (1-S1)*(-1.0)                      # loss piena prima di TP1
    E += S1*s1*d1                          # quota chiusa a TP1
    if be_mode=="IMMEDIATE":
        rem_stop = be_offset               # remainder stoppato a BE+offset
        p_stop_rem = 1-p_reach2
    else:                                  # DELAYED: BE solo dopo d1+be_delay*(d2-d1)
        d_be = d1 + be_delay*(d2-d1)
        p_be_armed = S(d_be)/S1
        # se BE non armato e reversal -> -1R sul remainder; se armato ma no d2 -> be_offset
        E += S1*(1-p_be_armed)*(1-s1)*(-1.0)*0.6   # 60% dei non-armati va a SL pieno, 40% comunque esce ~0
        rem_stop = be_offset
        p_stop_rem = p_be_armed - p_reach2 if p_be_armed>p_reach2 else 0
        E += S1*p_stop_rem*(1-s1)*rem_stop
        E += S1*p_reach2*( s2*d2 + s3*(p_full*runner_exit + (1-p_full)*d2*0.8) )
        return E - COST
    E += S1*p_stop_rem*(1-s1)*rem_stop
    E += S1*p_reach2*( s2*d2 + s3*(p_full*runner_exit + (1-p_full)*d2*0.8) )
    return E - COST

results=[]
for tp1pct, s1, s2, beo, mode in product(
        [0.40,0.50,0.60,0.70],
        [0.30,0.40,0.50,0.60],
        [0.20,0.30,0.40],
        [0.0,0.15,0.30],
        ["IMMEDIATE","DELAYED"]):
    if s1+s2>0.9: continue
    e = expectancy(tp1pct,s1,s2,beo,mode)
    results.append((e,tp1pct,s1,s2,beo,mode))

results.sort(reverse=True)
print("Config attuale (TP1=50%, 50/30/20, BE=0, IMMEDIATE):")
print(f"  Exp = {expectancy(0.50,0.50,0.30,0.0,'IMMEDIATE'):.3f}R\n")
print(f"{'Exp':>7} {'TP1%':>5} {'s1':>4} {'s2':>4} {'s3':>4} {'BE+':>5} {'Mode':>10}")
for e,t,s1,s2,beo,m in results[:10]:
    print(f"{e:>6.3f}R {t:>5.0%} {s1:>4.0%} {s2:>4.0%} {1-s1-s2:>4.0%} {beo:>5.2f} {m:>10}")
print("\nPeggiori 3 (da evitare):")
for e,t,s1,s2,beo,m in results[-3:]:
    print(f"{e:>6.3f}R {t:>5.0%} {s1:>4.0%} {s2:>4.0%} {1-s1-s2:>4.0%} {beo:>5.2f} {m:>10}")
