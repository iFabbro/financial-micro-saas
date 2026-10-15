from pathlib import Path
import shutil
import tarfile
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "release_bundle"

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)

include = [
    "README.md",
    "AGENTS.md",
    "docs/release-v1-notes.md",
    "pyproject.toml",
    "requirements.txt",
    "src",
    "tests",
    "db",
    "math_core.py",
]

for rel in include:
    src = ROOT / rel
    dst = OUT / rel
    if src.is_dir():
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".DS_Store",
                "*.bak",
                "*.bak2",
                ".pytest_cache",
            ),
        )
    elif src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

# optional artifacts safe to show
for rel in [
    "output/health_check_report.json",
    "output/health_check_report-2.txt",
]:
    src = ROOT / rel
    if src.exists():
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

manifest = []
for p in OUT.rglob("*"):
    if p.is_file():
        manifest.append(str(p.relative_to(OUT)))

(OUT / "MANIFEST.json").write_text(json.dumps(sorted(manifest), indent=2), encoding="utf-8")
(OUT / "MANIFEST.txt").write_text("\n".join(sorted(manifest)), encoding="utf-8")

archive = ROOT / "output" / "financial_micro_saas_demo_bundle.tar.gz"
if archive.exists():
    archive.unlink()

with tarfile.open(archive, "w:gz") as tar:
    tar.add(OUT, arcname="financial_micro_saas_demo_bundle")

print(archive)
print(OUT)
