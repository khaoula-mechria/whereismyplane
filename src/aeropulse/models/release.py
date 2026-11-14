"""Artefacts du classifieur retenu (T4.9, R-18) : export versionné par empreinte.

Copie ``classifier.json`` et une ``meta.json`` épurée (sans paramètres de régression, ADR-0017)
et écrit ``manifest.json`` (SHA-256, version du modèle, seuil). Le régresseur n'est pas exporté.
Commande : ``uv run python -m aeropulse.models.release``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_release(model_dir: Path, out_dir: Path) -> dict[str, Any]:
    meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
    params = {k: v for k, v in meta["params"].items() if k != "regression"}
    release_meta = {
        **meta,
        "params": params,
        "task": "classification",
        "regression": "reportée (ADR-0017)",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(model_dir / "classifier.json", out_dir / "classifier.json")
    (out_dir / "meta.json").write_text(json.dumps(release_meta, indent=2), encoding="utf-8")
    digest = _sha256(out_dir / "classifier.json")
    manifest = {
        "model_version": f"clf-{digest[:12]}",
        "threshold": meta["threshold"],
        "files": {name: _sha256(out_dir / name) for name in ("classifier.json", "meta.json")},
        "feature_columns": meta["feature_columns"],
        "horizon_hours": meta["horizon_hours"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-dir", type=Path, default=Path("data/ml/models"))
    p.add_argument("--out-dir", type=Path, default=Path("data/ml/release"))
    args = p.parse_args(argv)
    print(json.dumps(export_release(args.model_dir, args.out_dir), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
