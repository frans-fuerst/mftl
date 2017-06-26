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
        market, th.count(), th.duration() / 3600))

    data = th.data()

    trade_rates = [e['total'] / e['amount'] for e in data]
    trade_times = [e['time'] - now for e in data]

    # generate 5min-buckets
    candlestick_data = th.rate_buckets()
    times2 = [e['time'] - now for e in candlestick_data]
    rates2 = [(e['total_sell'] + e['total_buy']) /
              (e['amount_sell'] + e['amount_buy']) for e in candlestick_data]
    rates_slow = mftl.sma(rates2, 120)
    rates_fast = mftl.sma(rates2, 20)
    times2, rates2, rates_fast, rates_slow = mftl.trim(times2, rates2, rates_fast, rates_slow)
    print(len(times2), len(rates2), len(rates_fast), len(rates_slow))

    w = mftl.qwtgraph.GraphUI()
#    w.set_data(trade_times, trade_rates, 'gray')
    w.set_data(times2, rates2, 'blue')
    w.set_data(times2, rates_fast, 'fat_red')
    w.set_data(times2, rates_slow, 'fat_blue')
    # ---

    amount_C1 = 100.
    amount_C2 = 0.

    #return
    trades = 0
    last_C1 = 0
    last_C2 = 0
    FEE = 0.9975
    for i, d in enumerate(rates2):
        if i == 0: continue
        # verkaufen, wenn fast MA
        action = ('buy' if rates_fast[i] >= rates_slow[i] and rates_fast[i - 1] < rates_slow[i - 1] else
                  'sell' if rates_fast[i] <= rates_slow[i] and rates_fast[i - 1] > rates_slow[i - 1] else
                  'none')
        if action == 'none': continue
        if action == 'buy':
            if amount_C1 == 0.: continue
            new_c2 = amount_C1 / d * FEE
            amount_C2 = new_c2
            last_C1, amount_C1 = amount_C1, 0.
        elif action == 'sell':
            if amount_C2 == 0.: continue
            new_c1 = amount_C2 * d * FEE
            amount_C1 = new_c1
            last_C2, amount_C2 = amount_C2, 0.
        w.add_vmarker(times2[i], 'red' if action == 'sell' else 'green')
        w.add_hmarker(d, 'red' if action == 'sell' else 'green')
        trades += 1
        print('%.4d %.7d %9.2f %11.2f %11.9f %s' % (
            i, times2[i], amount_C1, amount_C2, d, action))

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
        while history.duration() < min_duration:
            log.info('fetch %r trade history (current: %.1fh)..',
                market,  history.duration() / 3600)
            try:
                history.fetch_next(api=mftl.px.PxApi, max_duration=-1)
                history.save()
            except mftl.util.ServerError as exc:
                log.warning('error occured: %r', exc)
                time.sleep(1)
        log.info('%r, #trades: %d, duration: %.1fh',
            market, history.count(), history.duration() / 3600)

    elif args.cmd == 'show':
        with mftl.qwtgraph.qtapp() as app:
            for f in os.listdir():
                if not f.startswith('trade_history'): continue
                show_curve(f.split('.')[0].split('-')[1])
            app.run()



if __name__ == '__main__':
    main()

