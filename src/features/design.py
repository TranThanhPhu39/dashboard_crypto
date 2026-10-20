from src.utils.project import *

def controls(p,asset,lags=5):
    x=p[list(SHOCKS)].copy()
    for k in range(1,lags+1):
        for c in list(SHOCKS)+[asset+'_return_pct']:
            # Crypto bar D-1 fixes at origin D; with a 24h availability buffer it
            # cannot enter controls yet. First admissible return is D-2.
            x[f'L{k}_{c}']=p[c].shift(k+1 if c==asset+'_return_pct' else k)
    return x

def daily_outcome(p,asset,h):
    return sum(p[asset+'_return_pct'].shift(-k) for k in range(h))

def LP_frame(p,asset,h,interaction=False):
    x=controls(p,asset)
    if interaction:
        x['stress']=p.stress
        for c in SHOCKS:x[c+'_stress']=p[c]*p.stress
    return x.assign(outcome=daily_outcome(p,asset,h)).dropna()
