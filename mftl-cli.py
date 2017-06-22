#!/usr/bin/env python3

import os, sys
import ast
import logging as log
import argparse
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import mftl
import mftl.px
import mftl.qwtgraph


def show_curve(market):
    now = time.time()

    th = mftl.TradeHistory(market)
    th.load()
    if not th.count(): return

    print('%r, #trades: %d, duration: %.1fh' % (
        market, th.count(), th.get_duration() / 3600))

    data = th.data()

    trade_rates = [e['total'] / e['amount'] for e in data]
    trade_times = [e['time'] - now for e in data]

    # generate 5min-buckets
    candlestick_data = th.rate_buckets()
    times2 = [e['time'] - now for e in candlestick_data]
    rates2 = [(e['total_sell'] + e['total_buy']) /
              (e['amount_sell'] + e['amount_buy']) for e in candlestick_data]

    w = mftl.qwtgraph.GraphUI()
    w.set_data(trade_times, trade_rates, 'gray')
    w.set_data(times2, rates2, 'fat_blue')

    w.show()


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


def create_personal_px_instance():
    try:
        return mftl.px.PxApi(**ast.literal_eval(open('../k').read()))
    except FileNotFoundError:
        log.warning('did not find key file - only public access is possible')
        raise


def main():
    args = get_args()
    log.basicConfig(level=log.DEBUG if args.verbose else log.INFO)
    mftl.util.ALLOW_CACHED_VALUES = 'ALLOW' if args.allow_cached else 'NEVER'

    if args.cmd == 'fetch':
        market = args.arg1
        history = mftl.TradeHistory(args.arg1)
        history.load()
        min_duration = int(args.arg2) if args.arg2 else 3600
        while history.get_duration() < min_duration:
            print('fetch..')
            history.fetch_next(api=mftl.px.PxApi)
        history.save()
        print('%r, #trades: %d, duration: %.1fh' % (
            market, history.count(), history.get_duration() / 3600))

    elif args.cmd == 'show':
        with mftl.qwtgraph.qtapp() as app:
            for f in os.listdir('..'):
                if not f.startswith('trade_history'): continue
                show_curve(f.split('.')[0].split('-')[1])
            app.run()



if __name__ == '__main__':
    main()

