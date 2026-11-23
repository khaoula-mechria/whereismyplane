import sys
import json
import time

sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import xgboost as xgb

from aeropulse import config
from aeropulse.models import evaluate
from aeropulse.models.train import _categorical_dtypes

SP = "data/eda/"
ml = pd.read_parquet("data/ml/ml_dataset.parquet")
ml = ml[ml.split.isin(["train", "validation"])].copy()  # le test n'est pas chargé
keys = ["flight_date", "carrier", "flight_number", "origin", "scheduled_departure_utc"]
intr = pd.read_parquet(SP + "intraday_keys.parquet").join(pd.read_parquet(SP + "intraday.parquet"))
ml = ml.merge(intr, on=keys, how="left", validate="one_to_one")
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
INTRA = ["lr3", "md3", "n3", "lr18", "md18"]
WX = ["wx_ts", "wx_snow", "wx_rain", "wx_freezing", "wx_fog", "wx_heavy", "gust3"]
BASE = list(config.FEATURE_COLUMNS)
params = {
    k: v
    for k, v in json.load(open("src/aeropulse/models/tuned_params.json"))["classification"].items()
}
tr, va = ml[ml.split == "train"], ml[ml.split == "validation"]
dtypes = _categorical_dtypes(tr)
y_tr, y_va = tr.is_delayed.astype(float).values, va.is_delayed.astype(float).values


def X(df, cols):
    x = df[cols].copy()
    for c in cols:
        if c not in config.CATEGORICAL_FEATURES:
            x[c] = pd.to_numeric(x[c].astype("float64"), errors="coerce")
    for c, dt in dtypes.items():
        if c in cols:
            v = x[c].astype(str)
            x[c] = pd.Categorical(v.where(v.isin(dt.categories)), dtype=dt)
    return x


variants = {
    "actuel (25 variables)": BASE,
    "+ retards du jour avant T-2h": BASE + INTRA,
    "+ phénomènes météo": BASE + WX,
    "+ les deux": BASE + INTRA + WX,
    "+ les deux, sans mois ni doublons": [
        c
        for c in BASE + INTRA + WX
        if c not in ("month", "scheduled_elapsed_minutes", "is_weekend", "dewpoint_c")
    ],
}
res = {}
for name, cols in variants.items():
    config.assert_no_forbidden_columns(cols)
    t = time.perf_counter()
    m = xgb.XGBClassifier(
        tree_method="hist",
        enable_categorical=True,
        n_jobs=-1,
        random_state=42,
        eval_metric="aucpr",
        **params,
    )
    m.fit(X(tr, cols), y_tr, verbose=False)
    p = m.predict_proba(X(va, cols))[:, 1]
    r = evaluate.classification_metrics(y_va, p)
    res[name] = {
        "pr_auc": round(r.pr_auc, 4),
        "roc_auc": round(r.roc_auc, 4),
        "f1": round(r.f1, 4),
        "precision": round(r.precision, 4),
        "recall": round(r.recall, 4),
        "calib": round(float(p.mean() - y_va.mean()), 4),
        "n_feat": len(cols),
    }
    print(
        f"{name:38s} PR-AUC {r.pr_auc:.3f} | ROC {r.roc_auc:.3f} | F1 {r.f1:.3f} (P {r.precision:.3f} R {r.recall:.3f}) | calib {p.mean() - y_va.mean():+.3f} | {time.perf_counter() - t:.0f} s",
        flush=True,
    )
    if name == "+ les deux":
        imp = pd.Series(m.get_booster().get_score(importance_type="gain")).sort_values(
            ascending=False
        )
        print("   gain (top 10):", imp.head(10).round(1).to_dict())
json.dump(res, open(SP + "fe_results.json", "w"), indent=1, ensure_ascii=False)
