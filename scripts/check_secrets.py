"""Scan léger de secrets dans les fichiers suivis par git (CI, NFR-03, AC-19).

Détecte des motifs évidents (clés AWS, clé Mostly Right, clés privées). Ce n'est pas un
remplacement d'un scanner complet. Sortie : code 1 si un motif est trouvé ; la valeur
détectée n'est jamais affichée.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "clé d'accès AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "clé Mostly Right": re.compile(r"\bmr_(?:use|live|cli)_[A-Za-z0-9]{16,}\b"),
    "clé privée": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
SELF = Path(__file__).resolve()


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(line) for line in out.splitlines() if line]


def scan(paths: list[Path]) -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for path in paths:
        if path.resolve() == SELF or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits.extend((path, label) for label, rx in PATTERNS.items() if rx.search(text))
    return hits


def main() -> int:
    hits = scan(tracked_files())
    for path, label in hits:
        print(f"SECRET POSSIBLE ({label}) dans {path}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
