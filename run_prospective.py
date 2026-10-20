"""Audit and safely operate the already frozen prospective experiment."""
import argparse
from src.evaluation.release_preservation import install
install()
from src.evaluation import prospective_operations as operations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['audit', 'run', 'validate', 'product', 'package'])
    parser.add_argument('--refresh-capture', action='store_true', help='Archive fresh responses even if today already has a successful capture')
    args = parser.parse_args()
    operations.initialize()
    if args.stage == 'run':
        operations.run(refresh_capture=args.refresh_capture)
    elif args.stage == 'audit':
        operations.audit()
    elif args.stage == 'validate':
        operations.validate()
    elif args.stage == 'package':
        operations.package()
    if args.stage in ['run', 'audit', 'product']:
        operations.product()


if __name__ == '__main__':
    main()
