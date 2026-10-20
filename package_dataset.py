"""Package deliverables and original source data; exclude temporary diagnostics."""
from pathlib import Path
import json,hashlib,zipfile,argparse
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--research',action='store_true',help='Include research results, report, dashboard and analysis code.')
parser.add_argument('--var-calendar',action='store_true',help='Package the approved calendar VAR extension without overwriting the baseline ZIP.')
args=parser.parse_args()
if args.var_calendar: args.research=True
FILES=['README.md','requirements.txt','download_data.py','download_vintages.py','build_dataset.py','download_fomc_crypto.py','audit_dataset.py','prepare_forecast_design.py','package_dataset.py']
if args.research:
 FILES+=['requirements-research.txt','research_common.py','research_eda.py','research_econometrics.py','research_events.py','research_forecasting.py','research_report.py','run_research.py','validate_research.py','validate_dashboard.cjs']
 if (ROOT/'research_var_calendar.py').exists(): FILES+=['research_var_calendar.py','validate_var_calendar.py']
selected=[ROOT/n for n in FILES]
for p in (ROOT/'data').rglob('*'):
 if not p.is_file(): continue
 if p.suffix=='.html' or p.name.endswith('_request.txt'): continue
 selected.append(p)
if args.research:
 for folder in [ROOT/'outputs/research',ROOT/'notebooks']:
  selected.extend(p for p in folder.rglob('*') if p.is_file())
manifest={str(p.relative_to(ROOT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in selected}
mp=ROOT/'manifest.json'; mp.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
output=ROOT/('topic09_var_calendar_extension_20261017.zip' if args.var_calendar else 'topic09_research_baseline_20261017.zip' if args.research else 'topic09_research_dataset_20261017_design.zip')
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in selected+[mp]: z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 assert 'data/processed/fomc_crypto_statement_windows.csv' in z.namelist()
 assert 'data/processed/forecast_origins_vintage_macro.csv' in z.namelist()
 assert 'data/processed/forecast_btc_common_with_usd.csv' in z.namelist()
 assert 'data/processed/research_design.json' in z.namelist()
 if args.research:
  assert 'outputs/research/report.html' in z.namelist()
  assert 'outputs/research/dashboard/index.html' in z.namelist()
 if args.var_calendar: assert 'outputs/research/var_calendar_extension/report.html' in z.namelist()
print(json.dumps({'zip':str(output),'bytes':output.stat().st_size,'files':len(selected)+1,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))
