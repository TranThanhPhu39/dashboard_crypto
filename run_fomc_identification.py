"""Audit FOMC inputs, reproduce published shock decomposition and compare matched timing."""
import argparse
from src.evaluation.fomc_identification_common import init,check_protected

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['sources','audit','fit','influence','product','validate','package','all'])
    args=parser.parse_args();init()
    if args.stage in ['sources','all']:
        from src.data.fomc_identification_sources import collect
        collect()
    if args.stage in ['audit','all']:
        from src.models.fomc_identification import audit
        audit()
    if args.stage in ['fit','all']:
        from src.models.fomc_identification import fit
        fit()
    if args.stage in ['influence','all']:
        from src.models.fomc_identification import influence
        influence()
    if args.stage in ['product','all']:
        from src.fomc_identification_product import build
        build()
    if args.stage in ['validate','all']:
        from src.evaluation.validate_fomc_identification import run
        run()
    if args.stage=='package':
        from src.fomc_identification_product import package
        package()
    print('Old protected files unchanged:',check_protected())

if __name__=='__main__':main()
