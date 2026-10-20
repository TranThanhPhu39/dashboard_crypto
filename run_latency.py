"""Approved additional-day feature delay, separate models and actual-receipt forecasting."""
import argparse
from src.evaluation.latency_common import init,check_protected

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','train','compare','collect','forecast','labels','evaluate','product','validate','package','all'])
    parser.add_argument('--origin',help='UTC midnight, optional for forecast; defaults to next midnight')
    args=parser.parse_args();init()
    if args.stage in ['prepare','all']:
        from src.models.latency import prepare
        prepare()
    if args.stage in ['train','all']:
        from src.models.latency import train
        train()
    if args.stage=='compare':
        from src.models.latency import comparisons
        comparisons()
    if args.stage in ['collect','all']:
        from src.data.latency_snapshots import collect
        collect()
    if args.stage in ['forecast','all']:
        from src.evaluation.latency_live import forecast
        forecast(args.origin)
    if args.stage=='labels':
        from src.evaluation.latency_live import labels
        labels()
    if args.stage=='evaluate':
        from src.evaluation.latency_live import evaluate
        evaluate()
    if args.stage in ['product','all']:
        from src.latency_product import build
        build()
    if args.stage in ['validate','all']:
        from src.evaluation.validate_latency import run
        run()
    if args.stage=='package':
        from src.latency_product import package
        package()
    print('Old protected files unchanged:',check_protected())

if __name__=='__main__':main()
