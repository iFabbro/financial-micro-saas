from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"
PROFILES = {
    "demo": DB_DIR / "financial_demo.db",
    "real": DB_DIR / "financial_real.db",
    "test": DB_DIR / "financial_test.db",
}

def ensure_dir():
    DB_DIR.mkdir(parents=True, exist_ok=True)

def set_env(profile: str):
    path = PROFILES[profile]
    os.environ["FINANCIAL_DB_PATH"] = str(path)
    print(path)

def reset_db(profile: str):
    ensure_dir()
    path = PROFILES[profile]
    if path.exists():
        path.unlink()
    print(f"reset {path}")

def clone_real_to_demo():
    ensure_dir()
    src = PROFILES["real"]
    dst = PROFILES["demo"]
    if not src.exists():
        raise SystemExit(f"missing source db: {src}")
    shutil.copy2(src, dst)
    print(f"cloned {src} -> {dst}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "cmd",
        choices=[
            "use-demo",
            "use-real",
            "use-test",
            "reset-test",
            "reset-demo",
            "clone-real-to-demo",
        ],
    )
    args = ap.parse_args()

    if args.cmd == "use-demo":
        set_env("demo")
    elif args.cmd == "use-real":
        set_env("real")
    elif args.cmd == "use-test":
        set_env("test")
    elif args.cmd == "reset-test":
        reset_db("test")
    elif args.cmd == "reset-demo":
        reset_db("demo")
    elif args.cmd == "clone-real-to-demo":
        clone_real_to_demo()

if __name__ == "__main__":
    main()
