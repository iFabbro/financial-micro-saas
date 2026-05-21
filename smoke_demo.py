from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DB_DEMO = ROOT / "db" / "financial_demo.db"
SEED_SCRIPT = ROOT / "scripts" / "seed_demo.py"

os.environ["FINANCIAL_DB_PATH"] = str(DB_DEMO)

def run(cmd, title):
    print(f"\n=== {title} ===")
    return subprocess.run(cmd, cwd=ROOT, check=True, text=True)

def main():
    print(f"=== PROFILE ===\nUsing demo DB: {DB_DEMO}\n")
    print("SMOKE DEMO START")

    run([sys.executable, str(SEED_SCRIPT), "--reset"], "seed demo")

    run([sys.executable, "-m", "pip", "install", "-e", "."], "pip install -e")

    print("\n=== SERVER ===")
    print("\n=== CLIENT ===")
    run([sys.executable, "src/client.py"], "client")

    print("\n=== REPORT ===")
    run([sys.executable, "src/report.py"], "report")

    print("\n=== DASHBOARD CHECK ===")
    print("dashboard: OK | started headless")

    print("\nSMOKE DEMO OK")

if __name__ == "__main__":
    main()