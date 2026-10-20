"""Run the agreed research steps from the frozen data; never download or retune on test."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']: os.environ.setdefault(key,'2')
from research_common import ROOT,js
import importlib,hashlib,time

if __name__=='__main__':
 sources=[ROOT/'data/processed/daily_research_latest.csv',ROOT/'data/processed/research_design.json']
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
 logs=[]
 for name in ['research_eda','research_econometrics','research_events','research_forecasting','research_report']:
  start=time.time(); print('Starting',name,flush=True)
  importlib.import_module(name).main()
  logs.append({'step':name,'seconds':round(time.time()-start,2)})
 for p in sources: assert hashes[str(p.relative_to(ROOT))]==hashlib.sha256(p.read_bytes()).hexdigest()
 js({'source_sha256':hashes,'steps':logs,'source_data_unchanged':True},'run_log')
 print('Research pipeline finished.',flush=True)
