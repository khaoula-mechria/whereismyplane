"""Téléchargeur de sources avec manifeste (T1.1).

Par défaut : **dry-run** (requêtes HEAD, aucun fichier téléchargé). Le téléchargement réel
exige `--execute`, et les fichiers BTS exigent en plus `--accept-bts-licence-risk` : aucun
texte de licence BTS n'a pu être lu (docs/dataset-card.md §5), cette acceptation est une
décision explicite du propriétaire du projet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from aeropulse.data.manifest import SourceFile, bts_candidates, noaa_files, study_months

USER_AGENT = "aeropulse-research/0.0.1"
TIMEOUT_S = 60
CHUNK = 1024 * 1024


@dataclass(frozen=True)
class HeadResult:
    status: int
    size: int | None
    last_modified: str | None


@dataclass(frozen=True)
class Resolved:
    entry: SourceFile
    status: int
    size: int | None
    last_modified: str | None


HeadFn = Callable[[str], HeadResult]


def http_head(url: str) -> HeadResult:
    """HEAD ; si le serveur refuse HEAD (403/405), GET d'un seul octet (Range)."""

    def attempt(req: urllib.request.Request) -> HeadResult:
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                headers = resp.headers
                size = headers.get("Content-Length")
                crange = headers.get("Content-Range")
                if crange and "/" in crange:
                    total = crange.rsplit("/", 1)[1]
                    size = total if total.isdigit() else size
                return HeadResult(
                    resp.status,
                    int(size) if size and size.isdigit() else None,
                    headers.get("Last-Modified"),
                )
        except urllib.error.HTTPError as exc:
            return HeadResult(exc.code, None, None)

    base = {"User-Agent": USER_AGENT}
    result = attempt(urllib.request.Request(url, method="HEAD", headers=base))
    if result.status in (403, 405):
        result = attempt(urllib.request.Request(url, headers={**base, "Range": "bytes=0-0"}))
    return result


def resolve(candidates: Sequence[SourceFile], head: HeadFn) -> Resolved:
    """Premier candidat qui répond 200/206, sinon le dernier avec son statut d'erreur."""
    last: Resolved | None = None
    for entry in candidates:
        res = head(entry.url)
        last = Resolved(entry, res.status, res.size, res.last_modified)
        if res.status in (200, 206):
            return last
    assert last is not None
    return last


def build_plan(head: HeadFn, sources: str = "all") -> list[Resolved]:
    plan: list[Resolved] = []
    if sources in ("all", "bts"):
        plan += [resolve(bts_candidates(y, m), head) for y, m in study_months()]
    if sources in ("all", "noaa"):
        plan += [resolve([e], head) for e in noaa_files()]
    return plan


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def download_one(item: Resolved, raw_dir: Path) -> dict[str, object]:
    """Télécharge atomiquement (fichier .part puis renommage) ; réutilise un fichier complet."""
    dest = raw_dir / item.entry.relpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and item.size is not None and dest.stat().st_size == item.size:
        status = "déjà présent"
    else:
        part = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(item.entry.url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp, part.open("wb") as out:
            while chunk := resp.read(CHUNK):
                out.write(chunk)
        if item.size is not None and part.stat().st_size != item.size:
            part.unlink()
            raise OSError(f"taille inattendue pour {item.entry.url}")
        part.replace(dest)
        status = "téléchargé"
    return {
        **asdict(item.entry),
        "size_bytes": dest.stat().st_size,
        "sha256": sha256_of(dest),
        "status": status,
    }


def format_plan(plan: Sequence[Resolved]) -> str:
    lines = [f"{'source':5s} {'statut':>6s} {'taille (octets)':>16s}  fichier"]
    for r in plan:
        size = f"{r.size:,}".replace(",", " ") if r.size is not None else "?"
        lines.append(f"{r.entry.source:5s} {r.status:>6d} {size:>16s}  {r.entry.name}")
    known = sum(r.size or 0 for r in plan if r.status in (200, 206))
    bad = [r for r in plan if r.status not in (200, 206)]
    lines.append(
        f"total connu : {known:,} octets ; fichiers non résolus : {len(bad)}".replace(",", " ")
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None, head: HeadFn = http_head) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--source", choices=["all", "bts", "noaa"], default="all")
    p.add_argument("--execute", action="store_true", help="télécharge réellement (sinon dry-run)")
    p.add_argument(
        "--accept-bts-licence-risk",
        action="store_true",
        help="requis pour télécharger BTS : aucun texte de licence lu, risque accepté",
    )
    args = p.parse_args(argv)
    # Console Windows (cp1252) : forcer l'UTF-8 pour les accents.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    plan = build_plan(head, args.source)
    print(format_plan(plan))
    unresolved = [r for r in plan if r.status not in (200, 206)]

    if not args.execute:
        print("\nDry-run : rien n'a été téléchargé.")
        return 1 if unresolved else 0
    if unresolved:
        print("\nArrêt : des fichiers ne sont pas résolus, rien n'est téléchargé.", file=sys.stderr)
        return 1
    if any(r.entry.source == "bts" for r in plan) and not args.accept_bts_licence_risk:
        print(
            "\nArrêt : BTS exige --accept-bts-licence-risk (décision du propriétaire).",
            file=sys.stderr,
        )
        return 2

    records = [download_one(r, args.raw_dir) for r in plan]
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    manifest = args.raw_dir / "manifest.json"
    manifest.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(records)} fichiers ; manifeste : {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
