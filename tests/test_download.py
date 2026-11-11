from pathlib import Path

import pytest

from aeropulse.data import download, manifest


def test_study_months_cover_31_months() -> None:
    months = list(manifest.study_months())
    assert len(months) == 31
    assert months[0] == (2023, 1)
    assert months[-1] == (2025, 7)


def test_noaa_manifest_has_nine_files_for_three_stations() -> None:
    files = manifest.noaa_files()
    assert len(files) == 9
    assert {f.name.split("/")[1] for f in files} == {
        "74486094789.csv",
        "72503014732.csv",
        "72502014734.csv",
    }
    assert all(f.url.startswith("https://noaa-global-hourly-pds.s3.amazonaws.com/") for f in files)


def test_bts_candidates_try_both_name_patterns() -> None:
    plain, paren = manifest.bts_candidates(2023, 1)
    assert plain.name.endswith("1987_present_2023_1.zip")
    assert paren.name.endswith("(1987_present)_2023_1.zip")
    assert "%28" in paren.url and "(" not in paren.url


def test_resolve_falls_back_to_second_candidate() -> None:
    def head(url: str) -> download.HeadResult:
        if "%28" in url:
            return download.HeadResult(200, 1234, "x")
        return download.HeadResult(404, None, None)

    res = download.resolve(manifest.bts_candidates(2024, 5), head)
    assert res.status == 200 and res.size == 1234 and "%28" in res.entry.url


def test_dry_run_downloads_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def head(url: str) -> download.HeadResult:
        return download.HeadResult(200, 10, None)

    code = download.main(["--raw-dir", str(tmp_path / "raw")], head=head)
    assert code == 0
    assert not (tmp_path / "raw").exists()
    assert "Dry-run" in capsys.readouterr().out


def test_bts_requires_explicit_licence_flag(tmp_path: Path) -> None:
    def head(url: str) -> download.HeadResult:
        return download.HeadResult(200, 10, None)

    code = download.main(["--raw-dir", str(tmp_path / "raw"), "--execute"], head=head)
    assert code == 2
    assert not (tmp_path / "raw").exists()


def test_unresolved_files_block_execution(tmp_path: Path) -> None:
    def head(url: str) -> download.HeadResult:
        return download.HeadResult(404, None, None)

    code = download.main(
        ["--raw-dir", str(tmp_path / "raw"), "--execute", "--accept-bts-licence-risk"], head=head
    )
    assert code == 1
