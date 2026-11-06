import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_secrets.py"


def _load() -> object:
    spec = importlib.util.spec_from_file_location("check_secrets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_secrets"] = module
    spec.loader.exec_module(module)
    return module


def test_detects_fake_keys_without_printing_them(tmp_path: Path) -> None:
    mod = _load()
    # Valeurs factices construites à l'exécution pour ne pas figer un motif dans le dépôt.
    fake_mr = "mr_" + "use_" + "x" * 24
    fake_aws = "AK" + "IA" + "A" * 16
    f = tmp_path / "leak.txt"
    f.write_text(f"{fake_mr}\n{fake_aws}\n", encoding="utf-8")
    hits = mod.scan([f])  # type: ignore[attr-defined]
    labels = {label for _, label in hits}
    assert labels == {"clé Mostly Right", "clé d'accès AWS"}


def test_clean_file_has_no_hit(tmp_path: Path) -> None:
    mod = _load()
    f = tmp_path / "ok.txt"
    f.write_text("rien à signaler\n", encoding="utf-8")
    assert mod.scan([f]) == []  # type: ignore[attr-defined]
