import numpy as np
from math import comb
rows = """L London W 3231.4 3227.721 3233.29
S NY W 3202.31 3209.394 3198.634
S London W 3224.97 3228.426 3223.205
S NY W 3220.325 3226.755 3216.905
L London L 3297.5 3293.939 3299.437
L NY W 3298.955 3295.446 3300.735
S London W 3326.29 3336.308 3321.113
S NY L 3320.615 3326.205 3317.76
L London W 3392.585 3390.93 3393.458
S NY W 3415.28 3420.064 3412.795
S London W 3478.995 3485.941 3475.305
S London W 3308.055 3311.785 3306.13
S NY W 3330.115 3333.7 3328.215
S London W 3307.72 3310.969 3306.04
S NY L 3268.15 3277.761 3263.059
S NY W 3299.43 3304.067 3296.955
S London W 3317.525 3321.901 3315.25
L London W 3304.895 3302.517 3306.19
L NY W 3308.115 3304.566 3309.93
S London W 3234.425 3238.173 3232.51
L London W 3253.615 3248.779 3256.18
L London W 3260.66 3257.291 3262.4
S NY W 3317.185 3323.02 3314.085
L London W 3367.985 3359.248 3372.52
S NY W 3393.875 3401.982 3389.47
L London L 3392.49 3388.354 3394.665
S London L 3328.465 3337.091 3323.795
L London W 3326.755 3319.919 3330.435
S NY W 3336.5 3340.808 3334.235
S NY W 3234.995 3239.002 3232.86""".split("\n")
D = [r.split() for r in rows]
d = [x[0] for x in D]; ses = [x[1] for x in D]; win = np.array([x[2]=="W" for x in D])
E = np.array([float(x[3]) for x in D]); S = np.array([float(x[4]) for x in D]); T = np.array([float(x[5]) for x in D])
risk = np.abs(E-S); rew = np.abs(T-E); rr = rew/risk
print("n", len(D), "wins", win.sum(), "losses", (~win).sum())
print("risk $: min %.2f median %.2f max %.2f | reward $: min %.2f median %.2f max %.2f" % (risk.min(), np.median(risk), risk.max(), rew.min(), np.median(rew), rew.max()))
print("reward/risk: mean %.3f min %.3f max %.3f" % (rr.mean(), rr.min(), rr.max()))
R = np.where(win, rr, -1.0)
print("sum R %.2f mean R %.3f sd %.3f t %.2f" % (R.sum(), R.mean(), R.std(ddof=1), R.mean()/(R.std(ddof=1)/np.sqrt(len(R)))))
be = 1/(1+rr.mean()); print("break-even win rate %.3f (observed %.3f)" % (be, win.mean()))
def tail(n,k,p): return sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
n, k = len(D), int(win.sum())
for p in (0.5, be, 0.70, 0.75): print("P(>=%d wins of %d | true win rate %.3f) = %.4f" % (k, n, p, tail(n,k,p)))
# cost: one spread per trade in dollars
for s in (0.10, 0.30, 0.40):
    Rn = R - s/risk
    print("spread %.2f$: mean R %.3f (t %.2f) | cost per trade %.3f R | worst cost %.2f R (risk %.2f$)" % (s, Rn.mean(), Rn.mean()/(Rn.std(ddof=1)/np.sqrt(n)), (s/risk).mean(), (s/risk).max(), risk[(s/risk).argmax()]))
# probability shift: with spread, target needs +s and stop triggers s earlier => P(win) down by s/(risk+reward) for a driftless walk
for s in (0.10, 0.30, 0.40):
    p0 = (risk/(risk+rew)).mean(); p1 = ((risk-s)/(risk+rew)).mean()
    print("driftless benchmark win rate: no spread %.3f, spread %.2f$ %.3f" % (p0, s, p1))
# breakdowns
for name, mask in (("London", np.array([x=="London" for x in ses])), ("NY", np.array([x=="NY" for x in ses])), ("Long", np.array([x=="L" for x in d])), ("Short", np.array([x=="S" for x in d]))):
    print("%-7s n %2d wins %2d meanR %.3f" % (name, mask.sum(), win[mask].sum(), R[mask].mean()))
# drawdown in R
c = np.cumsum(R); dd = (np.maximum.accumulate(c) - c).max(); print("max drawdown %.2f R, final %.2f R" % (dd, c[-1]))
# small targets
print("targets under 2.0$:", int((rew<2).sum()), "| under 1.0$:", int((rew<1).sum()))
