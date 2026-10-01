"""The Round 257 instrument universe (pre-registered): every liquid non-stock MT5 broker symbol. Equities are excluded (hours, commissions)."""
INDICES = ["US100.cash", "US500.cash", "US30.cash", "US2000.cash", "GER40.cash", "UK100.cash", "FRA40.cash", "EU50.cash",
           "JP225.cash", "HK50.cash", "AUS200.cash", "SPN35.cash"]
METALS = ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "XCUUSD"]
ENERGY = ["USOIL.cash", "UKOIL.cash", "NATGAS.cash", "HEATOIL.c"]
AGRI = ["WHEAT.c", "CORN.c", "SOYBEAN.c", "COFFEE.c", "SUGAR.c", "COCOA.c", "COTTON.c"]
FX = ["EURUSD", "GBPUSD", "USDCHF", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "AUDNZD", "AUDCAD", "AUDCHF", "AUDJPY", "CHFJPY", "EURGBP",
      "EURJPY", "GBPJPY"]
OTHER = ["DXY.cash"]
CRYPTO = ["BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD", "BNBUSD", "ADAUSD", "DOGEUSD"]
ALL = INDICES + METALS + ENERGY + AGRI + FX + OTHER + CRYPTO
GROUP = {**{s: "index" for s in INDICES}, **{s: "metal" for s in METALS}, **{s: "energy" for s in ENERGY}, **{s: "agri" for s in AGRI},
         **{s: "fx" for s in FX}, "DXY.cash": "fx", **{s: "crypto" for s in CRYPTO}}
