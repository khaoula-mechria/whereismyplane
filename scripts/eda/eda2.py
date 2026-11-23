import sys

sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap
from sklearn.metrics import roc_auc_score as auc

f = pd.read_parquet(
    "data/processed/flights",
    columns=[
        "flight_date",
        "carrier",
        "flight_number",
        "origin",
        "scheduled_departure_utc",
        "departure_delay_minutes",
        "cancelled",
        "diverted",
        "ml_eligible",
        "is_delayed",
        "departure_hour",
    ],
)
f["sched"] = pd.to_datetime(f.scheduled_departure_utc).dt.tz_convert(None)
f["cut"] = f.sched - pd.Timedelta(hours=2)
f["actual"] = f.sched + pd.to_timedelta(
    f.departure_delay_minutes, unit="m"
)  # connu seulement après le départ réel
out = []
for org, g in f.groupby("origin"):
    dep = g[g.departure_delay_minutes.notna() & ~g.cancelled].sort_values("actual")
    t = dep.actual.values.astype("datetime64[ns]").astype(np.int64)
    dl = dep.departure_delay_minutes.values
    late = (dl > 15).astype(float)
    cs_n = np.arange(1, len(t) + 1)
    cs_d = np.cumsum(dl)
    cs_l = np.cumsum(late)
    c = g.cut.values.astype("datetime64[ns]").astype(np.int64)

    def win(hours):
        hi = np.searchsorted(t, c, side="right")
        lo = np.searchsorted(t, c - hours * 3600 * 10**9, side="right")
        n = hi - lo
        sd = np.where(hi > 0, cs_d[np.maximum(hi - 1, 0)], 0) - np.where(
            lo > 0, cs_d[np.maximum(lo - 1, 0)], 0
        )
        sl = np.where(hi > 0, cs_l[np.maximum(hi - 1, 0)], 0) - np.where(
            lo > 0, cs_l[np.maximum(lo - 1, 0)], 0
        )
        return (
            n,
            np.where(n > 0, sd / np.maximum(n, 1), np.nan),
            np.where(n > 0, sl / np.maximum(n, 1), np.nan),
        )

    n3, md3, lr3 = win(3)
    # vols partis depuis minuit local... approximé par 18 h glissantes
    n18, md18, lr18 = win(18)
    # charge programmée : départs prévus à l'origine dans l'heure du départ (connue à l'avance)
    s = np.sort(g.sched.values.astype("datetime64[ns]").astype(np.int64))
    sc = g.sched.values.astype("datetime64[ns]").astype(np.int64)
    load = np.searchsorted(s, sc + 30 * 60 * 10**9) - np.searchsorted(s, sc - 30 * 60 * 10**9)
    out.append(
        pd.DataFrame(
            {
                "idx": g.index,
                "n3": n3,
                "md3": md3,
                "lr3": lr3,
                "lr18": lr18,
                "md18": md18,
                "load": load,
            }
        )
    )
x = pd.concat(out).set_index("idx").sort_index()
f = f.join(x)
tr = f[f.ml_eligible & (pd.to_datetime(f.flight_date) <= "2024-06-30")].copy()
y = tr.is_delayed.astype(float).values
print("vols d'entraînement:", len(tr))
for col in ["lr3", "md3", "lr18", "md18", "n3", "load"]:
    v = tr[col].fillna(tr[col].median()).values
    print(
        f"{col:5s} couverture {tr[col].notna().mean():.3f} | PR-AUC seule {ap(y, v):.3f} | ROC {auc(y, v):.3f}"
    )
tr["lr3_bin"] = pd.cut(tr.lr3, [-0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0])
print(
    "\ntaux de retard selon la part de retards des 3 h avant T-2h à l'aéroport:\n",
    tr.groupby("lr3_bin", observed=True).is_delayed.agg(["mean", "size"]).round(3).T.to_string(),
)
tr["load_bin"] = pd.qcut(tr.load, 5, duplicates="drop")
print(
    "\nselon la charge programmée (départs ±30 min):\n",
    tr.groupby("load_bin", observed=True).is_delayed.agg(["mean", "size"]).round(3).T.to_string(),
)
f[["n3", "md3", "lr3", "lr18", "md18", "load"]].to_parquet("data/eda/intraday.parquet")
f[["flight_date", "carrier", "flight_number", "origin", "scheduled_departure_utc"]].to_parquet(
    "data/eda/intraday_keys.parquet"
)
