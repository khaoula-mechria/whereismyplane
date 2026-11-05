# AeroPulse (anciennement FlightWise) — Index de la documentation

Documentation de planification et de conception. Les décisions D-01 à D-17 ont été arbitrées ; les éléments « En attente de vérification » et les informations encore à fournir sont listés dans [05-decisions/decisions-pending.md](05-decisions/decisions-pending.md). Le développement ne commence pas pour les tâches qui en dépendent.

## Lire dans cet ordre

1. [01-planning/project-brief.md](01-planning/project-brief.md) — le projet en une page.
2. [01-planning/scope-and-constraints.md](01-planning/scope-and-constraints.md) — périmètre, hypothèses (A-xx), inconnues (U-xx).
3. [02-architecture/architecture-overview.md](02-architecture/architecture-overview.md) — architecture et alternatives.
4. [03-project-management/implementation-plan.md](03-project-management/implementation-plan.md) — phases, points go/no-go.
5. [05-decisions/decisions-pending.md](05-decisions/decisions-pending.md) — décisions tranchées, blocages et vérifications en attente.
6. [dataset-card.md](dataset-card.md) et [04-quality/cost-estimate.md](04-quality/cost-estimate.md) — dataset et coûts.

## Index complet

### 01 — Planification
| Document | Contenu |
|---|---|
| [project-brief.md](01-planning/project-brief.md) | Problème, solution, utilisateurs, indicateurs |
| [vision-and-objectives.md](01-planning/vision-and-objectives.md) | Vision, principes, objectifs OBJ-1…8 |
| [scope-and-constraints.md](01-planning/scope-and-constraints.md) | Périmètre, contraintes C-xx, hypothèses, inconnues |
| [requirements.md](01-planning/requirements.md) | FR-xx, NFR-xx, IR-xx |
| [use-cases.md](01-planning/use-cases.md) | UC-01…08 |
| [acceptance-criteria.md](01-planning/acceptance-criteria.md) | AC-01…25 |

### 02 — Architecture
| Document | Contenu |
|---|---|
| [architecture-overview.md](02-architecture/architecture-overview.md) | Style, alternatives, points de vigilance |
| [technology-stack.md](02-architecture/technology-stack.md) | Technologies, statut confirmé/proposé |
| [system-components.md](02-architecture/system-components.md) | CMP-01…18, structure du dépôt |
| [database-design.md](02-architecture/database-design.md) | Zones S3, tables logiques |
| [api-design.md](02-architecture/api-design.md) | Routes, contrats, outils |
| [security-design.md](02-architecture/security-design.md) | Menaces, IAM, LLM |
| Diagrammes | [contexte](02-architecture/diagrams/context.md) · [conteneurs](02-architecture/diagrams/containers.md) · [composants](02-architecture/diagrams/components.md) · [flux de données](02-architecture/diagrams/dataflow.md) · [ER](02-architecture/diagrams/er-diagram.md) · [séquences](02-architecture/diagrams/sequences.md) |

### 03 — Gestion de projet
| Document | Contenu |
|---|---|
| [implementation-plan.md](03-project-management/implementation-plan.md) | Phases, chemin critique, go/no-go, coûts |
| [roadmap.md](03-project-management/roadmap.md) | Livraisons R0…R4, maintenant/ensuite/plus tard |
| [task-breakdown.md](03-project-management/task-breakdown.md) | WP0…WP9, tâches T-x.y, traçabilité |
| [milestones.md](03-project-management/milestones.md) | M0…M8 et critères de sortie |
| [risk-register.md](03-project-management/risk-register.md) | R-01…21 |

### 04 — Qualité
| Document | Contenu |
|---|---|
| [cost-estimate.md](04-quality/cost-estimate.md) | Garde-fous de coût, estimation par service (à produire) |
| [testing-strategy.md](04-quality/testing-strategy.md) | Niveaux de test, fuite, assistant |
| [quality-attributes.md](04-quality/quality-attributes.md) | Attributs, tactiques, compromis |
| [deployment-strategy.md](04-quality/deployment-strategy.md) | Environnements, CI/CD, cycle de vie des coûts |

### 05 — Décisions
| Document | Contenu |
|---|---|
| [adr/](05-decisions/adr/README.md) | ADR-0001…0015 |
| [decisions-pending.md](05-decisions/decisions-pending.md) | Registre D-01…D-17 : statuts, blocages, traçabilité |

### Pilotage et données
| Document | Rôle |
|---|---|
| [ROADMAP.md](ROADMAP.md) | Les 9 étapes, critères de fin (stable) |
| [PROGRESS.md](PROGRESS.md) | État courant, prochaines actions (vivant) |
| [dataset-card.md](dataset-card.md) | Dataset NYC 2023–2025 : annoncé vs vérifié, licence, test de faisabilité T-2h |
| [data-dictionary.md](data-dictionary.md) | Dictionnaire de données (squelette, à remplir en T1.3) |
| [04-quality/cost-estimate.md](04-quality/cost-estimate.md) | Budget 100 USD/mois, garde-fous, estimation à produire (G0) |

## Conventions d'identifiants

FR/NFR/IR exigences · UC cas d'utilisation · AC critères d'acceptation · CMP composants · WP lots · T-x.y tâches · M jalons · R risques · ADR décisions · D décisions à approuver · A hypothèses · U inconnues · C contraintes · G points go/no-go.

Statuts utilisés dans les documents : **[Confirmé]** / **Tranché** (arbitré), **[Proposé]**, **[Hypothèse]**, **[Inconnu]**, **[À vérifier]** / **En attente de vérification** (annoncé mais non contrôlé).
