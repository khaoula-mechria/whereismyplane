import sys
import json

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from aeropulse import config
from aeropulse.data import weather
from aeropulse.models import evaluate
from aeropulse.models.train import _categorical_dtypes

SP = "data/eda/"
NS = 10**9
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
    ],
)
f["sched"] = pd.to_datetime(f.scheduled_departure_utc).dt.tz_convert(None)
f["cut"] = f.sched - pd.Timedelta(hours=2)
f["actual"] = f.sched + pd.to_timedelta(f.departure_delay_minutes, unit="m")


def window_stats(g_events_t, values, cut, hours):
    t = g_events_t
    cs = np.concatenate([[0], np.cumsum(values)])
    hi = np.searchsorted(t, cut, side="right")
    lo = np.searchsorted(t, cut - int(hours * 3600 * NS), side="right")
    return hi - lo, cs[hi] - cs[lo]


new = pd.DataFrame(index=f.index)
for (org), g in f.groupby("origin"):
    dep = g[g.departure_delay_minutes.notna() & ~g.cancelled].sort_values("actual")
    t = dep.actual.values.astype("datetime64[ns]").astype(np.int64)
    c = g.cut.values.astype("datetime64[ns]").astype(np.int64)
    n1, l1 = window_stats(t, (dep.departure_delay_minutes.values > 15).astype(float), c, 1)
    new.loc[g.index, "lr1"] = np.where(n1 > 0, l1 / np.maximum(n1, 1), np.nan)
    # annulations : un vol annulé programmé avant le cutoff est connu comme annulé à son heure programmée
    s = g.sort_values("sched")
    ts = s.sched.values.astype("datetime64[ns]").astype(np.int64)
    ns3, nc3 = window_stats(ts, s.cancelled.values.astype(float), c, 3)
    new.loc[g.index, "canc3"] = np.where(ns3 > 0, nc3 / np.maximum(ns3, 1), np.nan)
for (org, car), g in f.groupby(["origin", "carrier"]):
    dep = g[g.departure_delay_minutes.notna() & ~g.cancelled].sort_values("actual")
    t = dep.actual.values.astype("datetime64[ns]").astype(np.int64)
    c = g.cut.values.astype("datetime64[ns]").astype(np.int64)
    n3, l3 = window_stats(t, (dep.departure_delay_minutes.values > 15).astype(float), c, 3)
    new.loc[g.index, "car_lr3"] = np.where(n3 >= 3, l3 / np.maximum(n3, 1), np.nan)
    n6, d6 = window_stats(t, dep.departure_delay_minutes.values.astype(float), c, 6)
    new.loc[g.index, "car_md6"] = np.where(n6 >= 3, d6 / np.maximum(n6, 1), np.nan)
keys = ["flight_date", "carrier", "flight_number", "origin", "scheduled_departure_utc"]
extra = f[keys].join(new)
# tendance de pression et de visibilité (3 h avant T-2h)
obs = weather.read_noaa(sorted(Path("data/raw/noaa").glob("*/*.csv")))[
    ["airport", "observed_utc", "sea_level_pressure_hpa", "visibility_m"]
].sort_values("observed_utc")
ml = pd.read_parquet("data/ml/ml_dataset.parquet")
ml = ml[ml.split.isin(["train", "validation"])].copy()
intr = pd.read_parquet(SP + "intraday_keys.parquet").join(pd.read_parquet(SP + "intraday.parquet"))
ml = ml.merge(intr, on=keys, how="left").merge(extra, on=keys, how="left")
ml["cut"] = pd.to_datetime(ml.scheduled_departure_utc).dt.tz_convert(None) - pd.Timedelta(hours=2)
wx = pd.read_parquet(SP + "wx_roll.parquet").sort_values("t")
ml = pd.merge_asof(
    ml.sort_values("cut"),
    wx,
    left_on="cut",
    right_on="t",
    left_by="origin",
    right_by="airport",
    direction="backward",
).drop(columns=["t", "airport"])
ml["cut3"] = ml.cut - pd.Timedelta(hours=3)
o3 = obs.rename(columns={"sea_level_pressure_hpa": "slp_3h", "visibility_m": "vis_3h"})
ml = pd.merge_asof(
    ml.sort_values("cut3"),
    o3,
    left_on="cut3",
    right_on="observed_utc",
    left_by="origin",
    right_by="airport",
    direction="backward",
    tolerance=pd.Timedelta(hours=2),
).drop(columns=["observed_utc", "airport"])
ml["slp_trend3"] = ml.sea_level_pressure_hpa - ml.slp_3h
ml["vis_trend3"] = ml.visibility_m - ml.vis_3h
ml.to_parquet(SP + "ml_fe.parquet")
BASE = [
    c
    for c in config.FEATURE_COLUMNS
    if c not in ("month", "scheduled_elapsed_minutes", "is_weekend", "dewpoint_c")
]
INTRA = ["lr3", "md3", "n3", "lr18", "md18"]
WX = ["wx_ts", "wx_snow", "wx_rain", "wx_freezing", "wx_fog", "wx_heavy", "gust3"]
MORE = ["lr1", "canc3", "car_lr3", "car_md6", "slp_trend3", "vis_trend3"]
tr, va = ml[ml.split == "train"], ml[ml.split == "validation"]
dtypes = _categorical_dtypes(tr)
y_tr, y_va = tr.is_delayed.astype(float).values, va.is_delayed.astype(float).values


def X(df, cols):
    x = df[cols].copy()
    for c in cols:
        if c in dtypes:
            v = x[c].astype(str)
            x[c] = pd.Categorical(v.where(v.isin(dtypes[c].categories)), dtype=dtypes[c])
        else:
            x[c] = pd.to_numeric(x[c].astype("float64"), errors="coerce")
    return x


P = {
    k: v
    for k, v in json.load(open("src/aeropulse/models/tuned_params.json"))["classification"].items()
}


def run(name, cols, params, early=False):
    config.assert_no_forbidden_columns(cols)
    kw = dict(
        tree_method="hist",
        enable_categorical=True,
        n_jobs=-1,
        random_state=42,
        eval_metric="aucpr",
        **params,
    )
    m = xgb.XGBClassifier(**kw)
    if early:
        m.set_params(early_stopping_rounds=40)
        m.fit(X(tr, cols), y_tr, eval_set=[(X(va, cols), y_va)], verbose=False)
    else:
        m.fit(X(tr, cols), y_tr, verbose=False)
    p = m.predict_proba(X(va, cols))[:, 1]
    r = evaluate.classification_metrics(y_va, p)
    print(
        f"{name:44s} PR-AUC {r.pr_auc:.3f} | ROC {r.roc_auc:.3f} | F1 {r.f1:.3f} (P {r.precision:.3f} R {r.recall:.3f}) | calib {p.mean() - y_va.mean():+.3f}"
        + (f" | arbres {m.best_iteration + 1}" if early else ""),
        flush=True,
    )
    return m, r


run("réf. : base épurée + jour + météo", BASE + INTRA + WX, P)
run("+ fenêtre 1 h, annulations, compagnie, tendances", BASE + INTRA + WX + MORE, P)
for depth, lr in ((6, 0.05), (8, 0.05), (6, 0.03)):
    q = {**P, "max_depth": depth, "learning_rate": lr, "n_estimators": 1500}
    run(
        f"  réglage profondeur {depth}, pas {lr} (arrêt anticipé)",
        BASE + INTRA + WX + MORE,
        q,
        early=True,
    )
