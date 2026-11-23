import sys
import re

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import numpy as np
import pandas as pd

from aeropulse import config

st = {v: k for k, v in config.NOAA_STATIONS.items()}
frames = []
for p in sorted(Path("data/raw/noaa").glob("*/*.csv")):
    r = pd.read_csv(
        p,
        usecols=lambda c: (
            c in ("STATION", "DATE", "REPORT_TYPE", "REM", "OC1", "AA1", "VIS", "CIG", "SLP", "WND")
        ),
        dtype=str,
    )
    frames.append(r[r.REPORT_TYPE.str.strip().isin(["FM-15", "FM-16"])])
o = pd.concat(frames, ignore_index=True)
o["airport"] = o.STATION.map(st)
o["t"] = pd.to_datetime(o.DATE)
WX = re.compile(r"^(\+|-|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)*(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|HZ)*$")


def flags(rem):
    rem = rem if isinstance(rem, str) else ""
    body = rem.split(" RMK")[0]
    toks = [
        t
        for t in body.split()
        if len(t) >= 2 and WX.match(t) and not t.isdigit() and t not in ("VC",)
    ]
    s = " ".join(toks)
    return (
        "TS" in s,
        "SN" in s or "PL" in s,
        "RA" in s or "DZ" in s,
        "FZ" in s,
        "FG" in s,
        "BR" in s,
        s.startswith("+") or " +" in s,
    )


fl = np.array([flags(x) for x in o.REM])
for i, n in enumerate(
    ["wx_ts", "wx_snow", "wx_rain", "wx_freezing", "wx_fog", "wx_mist", "wx_heavy"]
):
    o[n] = fl[:, i]
g = o.OC1.fillna("").str.split(",").str[0]
o["gust_mps"] = pd.to_numeric(g, errors="coerce").where(lambda v: v < 999) / 10
print(
    "observations:",
    len(o),
    "| part avec orage:",
    round(o.wx_ts.mean(), 4),
    "neige:",
    round(o.wx_snow.mean(), 4),
    "pluie:",
    round(o.wx_rain.mean(), 4),
    "brouillard:",
    round(o.wx_fog.mean(), 4),
    "| rafales renseignées:",
    round(o.gust_mps.notna().mean(), 3),
)
print(
    "exemples de jetons détectés:",
    o.REM.dropna()
    .head(400)
    .map(
        lambda r: " ".join(
            t for t in r.split(" RMK")[0].split() if WX.match(t) and len(t) >= 2 and not t.isdigit()
        )
    )
    .loc[lambda s: s != ""]
    .head(8)
    .tolist(),
)
o = o.sort_values("t")
f = pd.read_parquet("data/ml/ml_dataset.parquet")
tr = f[f.split == "train"].copy()
tr["cut"] = pd.to_datetime(tr.scheduled_departure_utc).dt.tz_convert(None) - pd.Timedelta(hours=2)
tr["sched"] = tr.cut + pd.Timedelta(hours=2)
cols = [
    "t",
    "airport",
    "wx_ts",
    "wx_snow",
    "wx_rain",
    "wx_freezing",
    "wx_fog",
    "wx_mist",
    "wx_heavy",
    "gust_mps",
]
# phénomènes dans les 3 h précédant T-2h (agrégés), et "oracle" au départ (diagnostic seulement, jamais une variable)
o3 = o[cols].copy()
for c in ["wx_ts", "wx_snow", "wx_rain", "wx_freezing", "wx_fog", "wx_heavy"]:
    o3[c] = o3[c].astype(float)
roll = []
for a, g in o3.groupby("airport"):
    g = g.set_index("t").sort_index()
    r = g[["wx_ts", "wx_snow", "wx_rain", "wx_freezing", "wx_fog", "wx_heavy"]].rolling("3h").max()
    r["gust3"] = g.gust_mps.rolling("3h").max()
    r["airport"] = a
    roll.append(r.reset_index())
roll = pd.concat(roll).sort_values("t")
a = pd.merge_asof(
    tr.sort_values("cut"),
    roll,
    left_on="cut",
    right_on="t",
    left_by="origin",
    right_by="airport",
    direction="backward",
)
b = pd.merge_asof(
    tr.sort_values("sched"),
    roll.rename(columns=lambda c: c + "_dep" if c not in ("t", "airport") else c),
    left_on="sched",
    right_on="t",
    left_by="origin",
    right_by="airport",
    direction="backward",
)
y = a.is_delayed.astype(float)
print("\nphénomène vu dans les 3 h avant T-2h → taux de retard (part des vols concernés):")
for c in ["wx_ts", "wx_snow", "wx_rain", "wx_freezing", "wx_fog", "wx_heavy"]:
    m = a[c] == 1
    print(
        f"  {c:12s} oui {a.loc[m, 'is_delayed'].astype(float).mean():.3f} ({m.mean():.3%}) | non {a.loc[~m, 'is_delayed'].astype(float).mean():.3f}"
    )
yb = b.is_delayed.astype(float)
print(
    "\ndiagnostic (interdit comme variable) - orage dans les 3 h avant le DÉPART:",
    round(yb[b.wx_ts_dep == 1].mean(), 3),
    f"({(b.wx_ts_dep == 1).mean():.3%})",
)
gq = pd.qcut(a.gust3.fillna(0), [0, 0.8, 0.9, 0.97, 1], duplicates="drop")
print(
    "rafale max 3 h (m/s) → taux:",
    a.groupby(gq, observed=True).is_delayed.agg(["mean", "size"]).round(3).T.to_string(),
)
for c, src in (("visibility_m", tr), ("ceiling_m", tr)):
    q = (
        pd.cut(src[c], [-1, 1600, 4800, 8000, 99999])
        if c == "visibility_m"
        else pd.cut(src[c], [-1, 150, 300, 1000, 3000, 99999])
    )
    print(
        f"\n{c} → taux:",
        src.groupby(q, observed=True).is_delayed.agg(["mean", "size"]).round(3).T.to_string(),
    )
roll.to_parquet("data/eda/wx_roll.parquet")
