import sys

sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

ml = pd.read_parquet("data/ml/ml_dataset.parquet")
tr = ml[ml.split == "train"].copy()
va = ml[ml.split == "validation"].copy()
y = tr.is_delayed.astype(float)
d = tr.dep_delay
print("TRAIN", len(tr), "taux", round(y.mean(), 4))
q = d.quantile([0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]).round(1).to_dict()
print("quantiles retard:", q)
print(
    "part avance (<0):",
    round((d < 0).mean(), 3),
    "| 0-15:",
    round(((d >= 0) & (d <= 15)).mean(), 3),
    "| 15-60:",
    round(((d > 15) & (d <= 60)).mean(), 3),
    "| >60:",
    round((d > 60).mean(), 3),
    "| >180:",
    round((d > 180).mean(), 4),
)
print(
    "part des minutes de retard (>15) apportée par >60 min:",
    round(d[d > 60].sum() / d[d > 15].sum(), 3),
)


def rate(col, df=tr, top=None):
    g = (
        df.groupby(col, observed=True)
        .is_delayed.agg(["mean", "size"])
        .sort_values("size", ascending=False)
    )
    if top:
        g = g.head(top)
    return g.assign(mean=lambda x: x["mean"].round(3))


print("\nheure:\n", rate("departure_hour").sort_index().T.to_string())
print("\njour (1=lun):\n", rate("day_of_week").sort_index().T.to_string())
print("\nmois (train):\n", rate("month").sort_index().T.to_string())
print("\ncompagnie:\n", rate("carrier").T.to_string())
print("\norigine:\n", rate("origin").T.to_string())
print("\nférié:", rate("is_holiday").T.to_string())
# variance expliquée par jour : combien de la variabilité vient de "jour x aéroport"
tr["day"] = pd.to_datetime(tr.flight_date)
dd = tr.groupby(["day", "origin"]).is_delayed.mean()
print(
    "\ntaux journalier par aéroport : moyenne",
    round(dd.mean(), 3),
    "écart-type",
    round(dd.std(), 3),
    "p10",
    round(dd.quantile(0.1), 3),
    "p90",
    round(dd.quantile(0.9), 3),
    "max",
    round(dd.max(), 3),
)
# part de la variance de y expliquée par la moyenne jour x aéroport (oracle intrajournalier)
m = tr.groupby(["day", "origin"]).is_delayed.transform("mean").astype(float)
print("R2 oracle 'taux du jour même à l'aéroport':", round(1 - ((y - m) ** 2).mean() / y.var(), 3))
mh = tr.groupby(["day", "origin", "departure_hour"]).is_delayed.transform("mean").astype(float)
from sklearn.metrics import average_precision_score as ap
from sklearn.metrics import roc_auc_score as auc

print("PR-AUC oracle jour×aéroport:", round(ap(y, m), 3), "| ROC", round(auc(y, m), 3))
