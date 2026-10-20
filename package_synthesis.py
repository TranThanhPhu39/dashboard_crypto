"""Package the consolidated report without overwriting earlier snapshots."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "topic09_lp_fomc_synthesis_20261017.zip"


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    selected = {
        p for p in ROOT.iterdir()
        if p.is_file() and (p.suffix in {".py", ".cjs", ".html"}
                            or p.name in {"README.md", "requirements.txt", "requirements-research.txt"})
    }
    for folder in ("data", "outputs/research", "notebooks"):
        for p in (ROOT / folder).rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            if p.name.endswith(("_alfred_form.html", "_alfred_error.html", "_request.txt")):
                continue
            selected.add(p)
    manifest = {}
    for p in sorted(selected):
        blob = p.read_bytes()
        manifest[p.relative_to(ROOT).as_posix()] = {"bytes": len(blob), "sha256": digest(blob)}
    mp = ROOT / "manifest_synthesis.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in sorted(selected):
            archive.write(p, p.relative_to(ROOT).as_posix())
        archive.write(mp, mp.name)
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        for name, expected in manifest.items():
            blob = archive.read(name)
            assert len(blob) == expected["bytes"] and digest(blob) == expected["sha256"], name
        required = [
            "README.md", "build_synthesis.py", "validate_synthesis.py", "package_synthesis.py",
            "outputs/research/synthesis/report.html", "outputs/research/synthesis/report.md",
            "outputs/research/synthesis/dashboard.html", "outputs/research/synthesis/method.json",
            "outputs/research/synthesis/independent_validation.json",
            "outputs/research/synthesis/browser_validation.json",
            "outputs/research/current_results_review.md",
            "outputs/research/fomc_comparison/report.html",
            "outputs/research/var_residual_diagnostics/report.html",
            "data/processed/forecast_btc_common_with_usd.csv",
        ]
        assert all(name in archive.namelist() for name in required)
        evidence = [n for n in archive.namelist()
                    if n.startswith("data/raw/usd_missing_verification/") and n.endswith(".html")]
        assert len(evidence) == 6
        assert json.loads(archive.read(mp.name)) == manifest
    result = {
        "zip": OUTPUT.name, "bytes": OUTPUT.stat().st_size,
        "files": len(manifest) + 1, "sha256": digest(OUTPUT.read_bytes()),
        "crc_check": True, "all_manifest_hashes_verified": True,
        "required_files_present": True, "official_Fed_evidence_html_count": len(evidence),
        "excluded": ["ALFRED download forms/errors/request payloads", "local dependencies and browser profiles", "earlier delivery ZIPs"],
    }
    (ROOT / "package_synthesis_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
