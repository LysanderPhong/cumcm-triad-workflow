#!/usr/bin/env python3
"""Compatibility entry point: create a new lean project with triad.py start."""
import argparse
import json
from triad import start

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    args = parser.parse_args()
    args.input = []
    try:
        print(json.dumps(start(args), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f'ERROR: {exc}\n')

if __name__ == '__main__':
    raise SystemExit(main())
