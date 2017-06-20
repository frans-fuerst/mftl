#!/usr/bin/env python3

import os, sys
import ast
import logging as log
import argparse
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import mftl
import mftl.px


def get_args() -> dict:
    parser = argparse.ArgumentParser(description='ticker')
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("-c", "--allow-cached", action='store_true')
    parser.add_argument('cmd')
    parser.add_argument('arg1', nargs='?')
    parser.add_argument('arg2', nargs='?')
    parser.add_argument('arg3', nargs='?')
    parser.add_argument('arg4', nargs='?')
    return parser.parse_args()


def main():
    args = get_args()
    log.basicConfig(level=log.DEBUG if args.verbose else log.INFO)
    mftl.util.ALLOW_CACHED_VALUES = 'ALLOW' if args.allow_cached else 'NEVER'
    try:
        api = mftl.px.PxApi(**ast.literal_eval(open('../k').read()))
    except FileNotFoundError:
        log.warning('did not find key file - only public access is possible')
        raise

    if args.cmd == 'fetch':
        history = mftl.TradeHistory(args.arg1)
        min_duration = int(args.arg2) if args.arg2 else 3600
        while history.get_duration() < min_duration:
            history.fetch_next(api=api)


if __name__ == '__main__':
    main()

