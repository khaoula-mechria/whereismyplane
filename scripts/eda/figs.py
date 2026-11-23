"""Graphiques de l'EDA T-2h (entraînement et validation uniquement ; le test n'est pas lu)."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SP = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
NAVY, BLUE, LIGHT, AMBER, GREY, RED = (
    "#0B1F3A",
    "#2F6FAE",
    "#8FB3D9",
    "#F2A541",
    "#5D6D7E",
    "#B8433A",
)
plt.rcParams.update(
    {
        "font.family": "Calibri",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": GREY,
        "axes.labelcolor": NAVY,
        "xtick.color": GREY,
        "ytick.color": GREY,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.titlesize": 13,
        "figure.dpi": 150,
    }
)

ml = pd.read_parquet(SP / "ml_fe.parquet")
tr = ml[ml.split == "train"].copy()
y = tr.is_delayed.astype(float)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 1. distribution du retard
fig, ax = plt.subplots(figsize=(8, 3.6))
d = tr.dep_delay.clip(-30, 180)
ax.hist(d, bins=np.arange(-30, 182, 3), color=LIGHT, edgecolor="white")
ax.hist(
    d[d > 15],
    bins=np.arange(-30, 182, 3),
    color=BLUE,
    edgecolor="white",
    label="retard > 15 min (cible = 1)",
)
ax.axvline(15, color=AMBER, lw=2)
ax.set_xlabel("Retard au départ (minutes ; borné à −30 et 180)")
ax.set_ylabel("Nombre de vols")
ax.set_title("61 % des vols partent en avance, 20 % ont plus de 15 min de retard")
ax.legend(frameon=False)
save(fig, "01_distribution_retard.png")

# 2. taux par heure
fig, ax = plt.subplots(figsize=(8, 3.4))
h = tr.groupby("departure_hour").is_delayed.apply(lambda s: s.astype(float).mean())
ax.bar(h.index, h.values * 100, color=BLUE)
ax.set_xlabel("Heure de départ programmée (heure locale)")
ax.set_ylabel("% de vols retardés")
ax.set_title("Le retard s'accumule dans la journée : 8 % à 6 h, 36 % à 23 h")
save(fig, "02_taux_par_heure.png")

# 3. saisonnalité instable
tvp = ml.assign(
    y_=pd.to_datetime(ml.flight_date).dt.year, m_=pd.to_datetime(ml.flight_date).dt.month
)
p = (
    tvp.pivot_table(
        index="m_", columns="y_", values="is_delayed", aggfunc=lambda s: s.astype(float).mean()
    )
    * 100
)
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.plot(p.index, p[2023], marker="o", color=BLUE, label="2023")
ax.plot(p.index, p[2024], marker="o", color=AMBER, label="2024")
ax.set_xticks(range(1, 13))
ax.set_xlabel("Mois")
ax.set_ylabel("% de vols retardés")
ax.set_title("La saison ne se répète pas d'une année à l'autre (septembre : 22 % → 12 %)")
ax.legend(frameon=False)
save(fig, "03_saisonnalite_instable.png")

# 4. variabilité journalière
dd = tr.groupby(["flight_date", "origin"]).is_delayed.apply(lambda s: s.astype(float).mean()) * 100
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.hist(dd, bins=40, color=BLUE, edgecolor="white")
ax.set_xlabel("% de vols retardés dans la journée, par aéroport")
ax.set_ylabel("Nombre de jours × aéroport")
ax.set_title("Un jour calme : 10 % ; un mauvais jour : 37 % et plus (max 76 %)")
save(fig, "04_variabilite_journaliere.png")

# 5. retards du jour connus avant T-2h
b = pd.cut(
    tr.lr3,
    [-0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0],
    labels=["0–5 %", "5–10 %", "10–20 %", "20–30 %", "30–50 %", "> 50 %"],
)
r = tr.groupby(b, observed=True).is_delayed.apply(lambda s: s.astype(float).mean()) * 100
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.bar(r.index.astype(str), r.values, color=[LIGHT, LIGHT, BLUE, BLUE, NAVY, NAVY])
for i, v in enumerate(r.values):
    ax.text(i, v + 1, f"{v:.0f} %", ha="center", color=NAVY)
ax.set_xlabel("Part des départs en retard dans les 3 h avant T-2h, même aéroport")
ax.set_ylabel("% de vols retardés")
ax.set_title("Le signal le plus fort : les retards déjà observés le jour même")
save(fig, "05_retards_du_jour.png")

# 6. phénomènes météo
labels = {
    "wx_ts": "Orage",
    "wx_freezing": "Pluie verglaçante",
    "wx_heavy": "Précipitation forte",
    "wx_snow": "Neige",
    "wx_fog": "Brouillard",
    "wx_rain": "Pluie",
}
rows = []
for c, lab in labels.items():
    m = tr[c] == 1
    rows.append((lab, tr.loc[m, "is_delayed"].astype(float).mean() * 100, m.mean() * 100))
rows.sort(key=lambda t: t[1])
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.barh([f"{l} ({s:.1f} % des vols)" for l, _, s in rows], [v for _, v, _ in rows], color=AMBER)
ax.axvline(y.mean() * 100, color=GREY, ls="--", lw=1.5)
ax.text(y.mean() * 100 + 1, -0.6, "moyenne 20 %", color=GREY)
ax.set_xlabel("% de vols retardés quand le phénomène est observé dans les 3 h avant T-2h")
ax.set_title("Les phénomènes météo comptent, les mesures brutes beaucoup moins")
save(fig, "06_phenomenes_meteo.png")

# 7. corrélations
num = [
    "departure_hour",
    "origin_hour_delay_rate_28d",
    "carrier_delay_rate_28d",
    "route_delay_rate_28d",
    "origin_delay_rate_28d",
    "lr3",
    "md3",
    "temperature_c",
    "dewpoint_c",
    "wind_speed_mps",
    "visibility_m",
    "ceiling_m",
    "sea_level_pressure_hpa",
    "gust3",
    "distance_miles",
    "scheduled_elapsed_minutes",
]
c = tr[num].astype(float).assign(cible=y).corr(method="spearman")
fig, ax = plt.subplots(figsize=(8.5, 7))
im = ax.imshow(c.values, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(c)), c.columns, rotation=60, ha="right", fontsize=9)
ax.set_yticks(range(len(c)), c.columns, fontsize=9)
for i in range(len(c)):
    for j in range(len(c)):
        if abs(c.values[i, j]) >= 0.3 and i != j:
            ax.text(
                j,
                i,
                f"{c.values[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if abs(c.values[i, j]) > 0.6 else NAVY,
            )
fig.colorbar(im, ax=ax, shrink=0.7, label="corrélation de Spearman")
ax.set_title(
    "Corrélations (entraînement) : doublons et faible lien de la météo brute avec la cible"
)
save(fig, "07_correlations.png")

# 8. gains par étape (validation)
steps = [
    ("Modèle actuel", 0.390),
    ("+ retards du jour avant T-2h", 0.443),
    ("+ phénomènes météo", 0.445),
    ("− mois et doublons", 0.445),
    ("+ 1 h, annulations, compagnie, tendances", 0.453),
    ("+ nouveau réglage", 0.457),
]
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.barh(
    [s for s, _ in steps][::-1],
    [v for _, v in steps][::-1],
    color=[NAVY, BLUE, BLUE, BLUE, BLUE, GREY],
)
for i, (_, v) in enumerate(steps[::-1]):
    ax.text(v + 0.003, i, f"{v:.3f}", va="center", color=NAVY)
ax.axvline(0.279, color=AMBER, ls="--", lw=1.5)
ax.text(0.282, 5.25, "référence 0,279", color=AMBER, fontsize=9)
ax.set_xlim(0.25, 0.49)
ax.set_xlabel("PR-AUC sur la validation (plus haut = meilleur)")
ax.set_title("De 0,390 à 0,457 sur la validation (+17 %)")
save(fig, "08_gains_validation.png")
print("figures :", sorted(p.name for p in OUT.glob("*.png")))
