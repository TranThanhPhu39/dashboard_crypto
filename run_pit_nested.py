"""py -3.11 run_pit_nested.py [audit|fit|compare|validate|product|all]."""
import argparse
from src.evaluation.release_preservation import install
install()
from src.evaluation.pit_nested_common import init, check_protected

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['audit','fit','compare','validate','product','all']);a=p.parse_args()
    init();check_protected()
    if a.stage in ['audit','all']:
        from src.evaluation.pit_feature_audit import prepare
        prepare()
    if a.stage in ['fit','all']:
        from src.models.pit_nested import train
        train()
    if a.stage in ['compare','all']:
        from src.models.pit_nested import compare
        compare()
    if a.stage in ['validate','all']:
        from src.evaluation.validate_pit_nested import validate
        validate()
    if a.stage in ['product','all']:
        from src.release_product import build
        build()
    print('Preserved old files:',check_protected(),flush=True)

if __name__=='__main__':main()
