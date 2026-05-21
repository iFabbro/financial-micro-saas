from pathlib import Path
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parent

def run(cmd, timeout=120):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)

results = []

required = [
    'pyproject.toml',
    'requirements.txt',
    'README.md',
    'AGENTS.md',
    'src',
    'tests',
    'db',
]
for rel in required:
    p = ROOT / rel
    results.append((rel, p.exists(), 'present' if p.exists() else 'missing'))

r = run([sys.executable, '-m', 'pip', 'install', '-e .'])
results.append(('pip install -e .', r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ''))

server = shutil.which('financial-mcp-server')
results.append(('financial-mcp-server', bool(server), server or 'not found'))
if server:
    r = run(['financial-mcp-server'], timeout=20)
    out = (r.stdout + '\n' + r.stderr).strip().splitlines()
    results.append(('server run', r.returncode == 0, out[:5]))

r = run([sys.executable, '-m', 'pytest', '-q'], timeout=180)
results.append(('pytest', r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ''))

dash = ROOT / 'src' / 'dashboard.py'
results.append(('streamlit dashboard', dash.exists(), 'src/dashboard.py' if dash.exists() else 'missing'))

for name, ok, info in results:
    print(f'{name}: {"OK" if ok else "FAIL"} | {info}')
