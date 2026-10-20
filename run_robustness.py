"""Versioned, post-hoc diagnostics; never overwrites the frozen blueprint."""
import argparse
from src.evaluation.robustness_common import init, check_protected

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['diagnostics','collect','product','validate','package','all'])
    args=parser.parse_args();init()
    if args.stage in ['diagnostics','all']:
        from src.evaluation.monetary_robustness import run as monetary
        from src.evaluation.joint_var_diagnostics import run as joint
        monetary();joint()
    if args.stage in ['collect','all']:
        from src.data.prospective_snapshots import collect
        collect()
    if args.stage in ['product','all']:
        from src.robustness_product import build
        build()
    if args.stage in ['validate','all']:
        from src.evaluation.validate_robustness import run
        run()
    if args.stage=='package':
        from src.robustness_product import package
        package()
    print('Frozen files unchanged:',check_protected())

if __name__=='__main__':main()
