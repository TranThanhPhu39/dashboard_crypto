"""Refresh only dashboard presentation from its existing embedded snapshot."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.dashboard_design import redesign

if __name__ == '__main__':
    path = ROOT / 'dashboard/index.html'
    raw = path.read_bytes()
    newline = '\r\n' if b'\r\n' in raw and raw.count(b'\r\n') == raw.count(b'\n') else '\n'
    source = path.read_text(encoding='utf-8')
    path.write_text(redesign(source), encoding='utf-8', newline=newline)
    print('Updated Orbit presentation; existing embedded research data retained.')
