import sys

sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

from aeropulse import config

ml = pd.read_parquet("data/ml/ml_dataset.parquet")
tv = ml[ml.split.isin(["train", "validation"])].copy()
tr = tv[tv.split == "train"]
num = [c for c in config.NUMERIC_FEATURES]
X = tr[num].astype(float)
y = tr.is_delayed.astype(float)
sp = X.assign(target=y).corr(method="spearman")
print("corrélation (Spearman) avec la cible, entraînement :")
print(sp["target"].drop("target").sort_values(key=abs, ascending=False).round(3).to_string())
pairs = []
for i, a in enumerate(num):
    for b in num[i + 1 :]:
        v = sp.loc[a, b]
        if abs(v) >= 0.6:
            pairs.append((a, b, round(v, 2)))
print("\npaires fortement corrélées (|rho| >= 0,6):", pairs)
tv["ym"] = pd.to_datetime(tv.flight_date).dt.to_period("M").astype(str)
m = (
    tv.groupby("ym")
    .agg(
        rate=("is_delayed", lambda s: s.astype(float).mean()),
        n=("is_delayed", "size"),
        mean_delay=("dep_delay", "mean"),
    )
    .round(3)
)
print("\ntaux mensuel (entraînement + validation):\n", m.T.to_string())
# même mois, années différentes
tv["y_"] = pd.to_datetime(tv.flight_date).dt.year
tv["m_"] = pd.to_datetime(tv.flight_date).dt.month
p = tv.pivot_table(
    index="m_", columns="y_", values="is_delayed", aggfunc=lambda s: s.astype(float).mean()
).round(3)
print("\nmême mois, 2023 vs 2024 :\n", p.T.to_string())
# l'historique 28 j prédit-il le mois suivant ? corrélation taux 28 j (aéroport) vs taux réel du jour
d = tr.groupby(["flight_date", "origin"]).agg(
    hist=("origin_delay_rate_28d", "mean"), real=("is_delayed", lambda s: s.astype(float).mean())
)
print(
    "\ncorrélation journalière taux historique 28 j vs taux réel du jour (aéroport):",
    round(d.corr().iloc[0, 1], 3),
)
# anomalies
print(
    "\ndurée programmée <= 0 :",
    int((tr.scheduled_elapsed_minutes <= 0).sum()),
    "| distance <= 0 :",
    int((tr.distance_miles <= 0).sum()),
)
