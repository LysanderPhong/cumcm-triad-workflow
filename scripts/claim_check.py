#!/usr/bin/env python3
"""Check current claim versions and actual run evidence in the single journal."""
import argparse
import json
from triad import check_claims, require_project, rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    args = parser.parse_args()
    try:
        p = require_project(args.project)
        errors = check_claims(p, rows(p))
        print(json.dumps({'status': 'INVALID' if errors else 'VALID', 'errors': errors}, ensure_ascii=False, indent=2))
        return 2 if errors else 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f'ERROR: {exc}\n')

if __name__ == '__main__':
    raise SystemExit(main())
