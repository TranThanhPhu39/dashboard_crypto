"""One entry point for the current structured project; never overwrite old research."""
import os,sys,argparse,subprocess
from pathlib import Path
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'2')
ROOT=Path(__file__).resolve().parent

def bootstrap():
    """On a fresh copy only, regenerate prerequisite snapshots using original scripts."""
    if (ROOT/'data/processed/daily_research_latest.csv').exists():raise RuntimeError('Bootstrap is only for a fresh copy; existing frozen data must not be regenerated.')
    for name in ['download_data.py','download_vintages.py','build_dataset.py','download_fomc_crypto.py','run_research.py']:
        subprocess.run([sys.executable,str(ROOT/name)],cwd=ROOT,check=True)
    for stage in ['prepare','fit','tests','stress']:subprocess.run([sys.executable,str(ROOT/'research_completion.py'),stage],cwd=ROOT,check=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['all','bootstrap','download','prepare','econometrics','quantile','models','product','validate','package','predict'])
    parser.add_argument('--download',action='store_true',help='Fetch Binance pages missing from the separate cache.')
    parser.add_argument('--features');parser.add_argument('--asset',choices=['btc','eth']);parser.add_argument('--variant',choices=['long_own','long_macro','common_own','common_macro','common_usd']);parser.add_argument('--target',choices=['return','squared_return']);parser.add_argument('--model',choices=['elastic_net','gradient_boosting']);args=parser.parse_args()
    if args.stage=='bootstrap':bootstrap();return
    from src.utils.project import init,OUT,save_json,sha,CONFIG
    init();logs=[]
    from src.data.binance import download
    from src.data.calendar import prepare
    from src.models.econometrics import run as econometrics
    from src.models.quantile import run as quantile
    from src.models.predictive import run as models
    from src.evaluation.prospective import protocol,predict
    def product():
        from src.product import build
        protocol();build()
    def validate():
        from src.evaluation.validate import run
        run();subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],cwd=ROOT,check=True)
        subprocess.run(['node',str(ROOT/'tests/validate_blueprint_dashboard.cjs')],cwd=ROOT,check=True)
        subprocess.run(['node',str(ROOT/'tests/preview_blueprint.cjs')],cwd=ROOT,check=True)
    def package():
        from src.utils.package import run
        run()
    stages={'download':lambda:download(args.download),'prepare':prepare,'econometrics':econometrics,'quantile':quantile,'models':models,'product':product,'validate':validate,'package':package}
    if args.stage=='predict':
        if not all([args.features,args.asset,args.variant,args.target,args.model]):parser.error('predict requires --features --asset --variant --target --model')
        predict(args.features,args.asset,args.variant,args.target,args.model);return
    import time
    chosen=list(stages) if args.stage=='all' else [args.stage]
    for name in chosen:
        if name=='package':save_json(OUT/'pipeline_last_run.json',dict(config_sha256=sha(CONFIG),steps=logs,package='see separate package audit beside ZIP'))
        start=time.time();stages[name]();logs.append(dict(stage=name,seconds=round(time.time()-start,3)))
        print('Finished project stage:',name,flush=True)
        if name!='package':save_json(OUT/'pipeline_last_run.json',dict(config_sha256=sha(CONFIG),steps=logs))

if __name__=='__main__':main()
