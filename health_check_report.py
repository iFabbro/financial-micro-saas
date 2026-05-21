from pathlib import Path
import subprocess
import sys
import shutil
import json
import datetime

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)

def run(cmd, timeout=120):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)

results = []

def add(name, ok, info):
    results.append({'name': name, 'ok': bool(ok), 'info': info})

for rel in ['pyproject.toml', 'requirements.txt', 'README.md', 'AGENTS.md', 'src', 'tests', 'db']:
    p = ROOT / rel
    add(rel, p.exists(), 'present' if p.exists() else 'missing')

r = run([sys.executable, '-m', 'pip', 'install', '-e', str(ROOT)], timeout=180)
add('pip install -e', r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else '')

server = shutil.which('financial-mcp-server')
add('financial-mcp-server', bool(server), server or 'not found')
if server:
    r = run(['financial-mcp-server'], timeout=20)
    add('server run', r.returncode == 0, (r.stdout + '\n' + r.stderr).strip().splitlines()[:5])

r = run([sys.executable, '-m', 'pytest', '-q'], timeout=240)
add('pytest', r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else '')

add('streamlit dashboard', (ROOT / 'src' / 'dashboard.py').exists(), 'src/dashboard.py')

summary = {
    'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
    'root': str(ROOT),
    'pass': sum(1 for x in results if x['ok']),
    'fail': sum(1 for x in results if not x['ok']),
    'results': results,
}

(OUT / 'health_check_report.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')

lines = [
    f"Health check report - {summary['timestamp']}",
    f"Root: {summary['root']}",
    f"Pass: {summary['pass']}  Fail: {summary['fail']}",
    ''
]
for x in results:
    lines.append(f"- {x['name']}: {'OK' if x['ok'] else 'FAIL'} | {x['info']}")

(OUT / 'health_check_report.txt').write_text('\n'.join(lines), encoding='utf-8')
print(OUT / 'health_check_report.txt')
print(OUT / 'health_check_report.json')
