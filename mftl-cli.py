#!/usr/bin/env python3

import os, sys
import ast
import logging as log
import argparse
import time
import itertools

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import mftl
import mftl.px
import mftl.qwtgraph
from mftl.qwtgraph import Pen

FEE = 0.9975
HOUR = 1 / 3600
DAY = 1 * HOUR / 24

def sliced(iterable, N):
    it = iter(iterable)
    return list(iter(lambda: list(itertools.islice(it, N)), []))


class Strategy:
    def __init__(self, fast_ma, medium_ma, slow_ma):
        self._fast_ma = fast_ma
        self._medium_ma = medium_ma
        self._slow_ma = slow_ma

    def feed(self, history, amount):
        trades = []
        plots = []
        #    data = th.data()
        #    trade_rates = [e['total'] / e['amount'] for e in data]
        #    trade_times = [e['time'] - now for e in data]

        # generate 5min-buckets
        bucket_data = history.rate_buckets()
        now = bucket_data[-1]['time']
        t_factor = 1 / 3600 / 24
        times = [(e['time'] - now) * t_factor for e in bucket_data]
        rates = [(e['total_sell'] + e['total_buy']) /
                 (e['amount_sell'] + e['amount_buy']) for e in bucket_data]
        rates_fast = mftl.sma(rates, self._fast_ma)
        rates_medium = mftl.sma(rates, self._medium_ma)
        rates_slow = mftl.sma(rates, self._slow_ma)
        times, rates, rates_fast, rates_medium, rates_slow = mftl.trim(
            times, rates, rates_fast, rates_medium, rates_slow)

        plots.append((times, ((rates, Pen.gray_fat),
                              (rates_medium, Pen.dark_cyan_fat),
                              (rates_fast, Pen.dark_magenta_fat),
                              (rates_slow, Pen.dark_yellow_fat),
                              )))

        amount_C1 = amount  # amount of primary coin we start with
        amount_C2 = 0.      # amount of secondary coin (asset) we start with

        last_C1 = 0
        last_C2 = 0
        for i, d in enumerate(rates):
            if i == 0: continue
            # verkaufen, wenn fast MA
            action = ('buy' if (rates_fast[i] >= rates_medium[i] and
                                rates_fast[i - 1] < rates_medium[i - 1] and
                                rates_fast[i] > rates_slow[i]) else
                      'sell' if (rates_fast[i] <= rates_medium[i] and
                                 rates_fast[i - 1] > rates_medium[i - 1] and
                                 rates_fast[i] < rates_slow[i]) else
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
            trades.append((action, times[i], d))
#            print('%.4d %.7d %9.2f %11.2f %11.9f %s' % (
#                i, times[i], amount_C1, amount_C2, d, action))

        if trades and trades[-1][0] == 'buy':
            del trades[-1]

        return last_C1, trades, plots

    def plot(self, market, gain, trades, plots):
        w = mftl.qwtgraph.GraphUI('%s - %.1f%%' % (market, gain))
        for t, p in plots:
            for curve, color in p:
                w.set_data(t, curve, color)

        for (a1, t1, v1), (a2, t2, v2) in sliced(trades, 2):
            w.add_vmarker(t1, Pen.dark_green)
            w.add_vmarker(t2, Pen.dark_red)
            #            w.add_hmarker(v, 'red' if a == 'sell' else 'green')
            w.add_line(t1, v1, t2, v2, Pen.green_fat if v2 >= v1 else Pen.red_fat)

        w.show()


def show_curve(market):
    th = mftl.TradeHistory(market)
    th.load()
    if not th.count(): return

    print('%r, #trades: %d, duration: %.1fh' % (
        market, th.count(), th.duration() / 3600))
    m = ((0, [],[]), market, 0, 0, 0)

    #for s in range(20):
            #fast = f + 1
            #slow = fast + s + 1
    fast = 30 #20
    medium = 50 #35
    slow = 250 #medium + 50 * s #70

    strategy = Strategy(fast, medium, slow)
    g = strategy.feed(th, 100), market, fast, medium, slow
    #m = max(g, m)
    print(g[1:], m[1:])
    strategy.plot(market, *g[0])



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
                market,  history.duration() * HOUR)
            try:
                history.fetch_next(api=mftl.px.PxApi, max_duration=-1)
                history.save()
            except mftl.util.ServerError as exc:
                log.warning('error occured: %r', exc)
                time.sleep(1)
        log.info('%r, #trades: %d, duration: %.1fh',
            market, history.count(), history.duration() * HOUR)

    elif args.cmd == 'show':
        with mftl.qwtgraph.qtapp() as app:
            for f in os.listdir():
                if not f.startswith('trade_history'): continue
                if args.arg1 and f.lower().find(args.arg1.lower()) < 0: continue
                show_curve(f.split('.')[0].split('-')[1])
            app.run()



if __name__ == '__main__':
    main()

