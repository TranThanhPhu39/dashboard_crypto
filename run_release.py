"""Maintained submission entry point; never refits or scores early."""
import argparse,os
from src.evaluation.release_preservation import install,validate

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['build','validate','operate','validate-pit','package','all'])
    p.add_argument('--refresh-capture',action='store_true',help='Archive new immutable source responses during an operational run')
    a=p.parse_args();install()
    if a.refresh_capture and a.stage!='operate':p.error('--refresh-capture requires operate')
    if a.stage=='operate':
        from src.automation_runtime import assert_writer_allowed,HostedAuthorityError
        try:
            assert_writer_allowed()
        except HostedAuthorityError as exc:
            p.exit(78,str(exc)+'\n')
        from src.evaluation import prospective_operations as op
        if os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('TOPIC09_FRED_TRANSPORT')=='official-api':
            from src.data.github_fred_api import install as install_api_transport
            install_api_transport()
        from src.automation_runtime import process_lock,AlreadyRunningError,OUT as AUTO,operate_frozen
        try:
            with process_lock(AUTO/'operate.lock'):
                op.initialize();operate_frozen(op,refresh_capture=a.refresh_capture);op.product()
                from src.release_product import build
                from src.evaluation.validate_release import validate as validate_product
                build();validate_product()
        except AlreadyRunningError:
            print('Another pipeline run is active; no duplicate mutations.',flush=True)
            raise SystemExit(75)
    elif a.stage=='validate-pit':
        from src.evaluation.validate_pit_nested import validate as validate_pit
        validate_pit()
    elif a.stage=='package':
        from src.release_product import package
        package()
    else:
        validate()
        if a.stage in ['build','all']:
            from src.release_product import build
            build()
        from src.evaluation.validate_release import validate as validate_product
        validate_product()

if __name__=='__main__':main()
