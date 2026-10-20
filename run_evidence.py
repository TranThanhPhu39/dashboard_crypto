"""Independent literature-motivated identification and volatility forecasting extension."""
import argparse
from src.evaluation.release_preservation import install
install()
from src.evaluation.evidence_common import init,check_protected

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['preflight','sources','causal','rotations','rv_prepare','rv_fit','prospective','product','validate','package','all'])
    a=p.parse_args();init()
    if a.stage=='preflight':
        from src.data.evidence_sources import preflight
        preflight()
    if a.stage in ['sources','all']:
        from src.data.evidence_sources import fetch,BS_URL,RAW,minutes,rv_archives
        fetch(RAW/'bauer_swanson.xlsx',BS_URL);minutes();rv_archives()
    if a.stage in ['causal','all']:
        from src.models.evidence_causal import prepare,fit
        prepare();fit()
    if a.stage in ['rotations','all']:
        from src.models.evidence_rotations import run
        run()
    if a.stage in ['rv_prepare','all']:
        from src.models.evidence_rv import prepare
        prepare()
    if a.stage in ['rv_fit','all']:
        from src.models.evidence_rv import fit
        fit()
    if a.stage in ['prospective','all']:
        from src.evaluation.evidence_live import run
        run()
    if a.stage in ['validate','all']:
        from src.evaluation.validate_evidence import run
        run()
    if a.stage in ['product','all']:
        from src.release_product import build
        build()
    if a.stage=='package':
        from src.evidence_product import package
        package()
    print('Old protected files unchanged:',check_protected(),flush=True)

if __name__=='__main__':main()
