from .util import get_EUR, json_mod, get_btc_rates

import logging as log
import threading
import os
import time
import numpy as np

class DiscontiguousLists(ValueError):
    pass

def get_long_name(short_name: str) -> str:
    try:
        return {
            'BTC':   'BC',
            'USDT':  'USDTether',
            'ETH':   'Ethereum',
            'ETC':   'Eth. Cl.',
            'XMR':   'Monero',
            'LTC':   'Litecoin',
            'BCN':   'Bytecoin',
            'XVC':   'VCASH',
            'BTS':   'Bitshare',
            'NXT':   'Nxt',
            'AMP':   'Synereo',
            'VTC':   'Vertcoin',
            'XRP':   'Ripple',
            'DASH':  'Dash',
            'GNT':   'Golem',
            'FLO':   'Florin',
            'BURST': 'Burst',
            'SC':    'Siacoin',
            'DOGE':  'Dodgecoin',
            'GRC':   'Gridcoin',
            'STRAT': 'Stratis',
            'XEM':   'NEM',
            'FCT':   'Factom',
            'POT':   'PotCoin',
            }[short_name]
    except KeyError:
        return 'unknown(%s)' % short_name


def sma(data, N):
    N_ret = 1. / N
    cumsum = np.cumsum(np.insert(data, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) * N_ret


def ema(data, alpha):
    ''' returns eponential moving average
    '''
    alpha_n = 1 - alpha
    result = []
    n = data[0]
    for x in data:
        n = alpha * x + alpha_n * n
        result.append(n)
    return result


def vema(totals, amounts, a):
    ''' returns the volume weighted eponential moving average
    '''
    smooth_totals = ema(totals, a)
    smooth_amounts = ema(amounts, a)
    return [t / c for t, c in zip(smooth_totals, smooth_amounts)]


def trim(*lists):
    def trim_one(l, N):
        length = len(l)
        if length == N: return l
        if isinstance(l, list):
            del l[:length - N]
        elif isinstance(l, np.ndarray):
            l = l[length - N:]
        return l

    min_len = min(len(x) for x in lists)
    return (trim_one(l, min_len) for l in lists)


def sum_trades(history: list) -> tuple:
    total = 0.0
    amount = 0.0
    min_rate = +99999999
    max_rate = -99999999
    for t in history:
        total += t['total']
        amount += t['amount']
        min_rate = min(min_rate, t['rate'])
        max_rate = max(max_rate, t['rate'])
    return total, amount, min_rate, max_rate


def expand_bucket(bucket):
    amount = bucket['amount_buy'] + bucket['amount_sell']
    total = bucket['total_buy'] + bucket['total_sell']
    return {**bucket, **{
        'amount': amount,
        'total': total,
        'rate': total / amount,
    }}


def extract_coin_data(ticker_data):
    coins = {}
    for m in ticker_data:
        c1, c2 = m.split('_')
        if not c1 in coins: coins[c1] = set()
        coins[c1].add(c2)
    return coins


class TraderData:
    def __init__(self):
        self._last_thread = None
        self._balances = {}
        self._trade_history = {}
        self._btc_usd_price = 0.
        self._eur_price = 0.
        self._open_orders = []
        self._available_coins = {}
        self._available_markets = set()
        self._market_history = {}

    def _called_from_same_thread(self):
        thread_id = threading.current_thread().ident
        if not self._last_thread:
            self._last_thread = thread_id
        return self._last_thread == thread_id

    def create_trade_history(self, market, max_duration=24*3600):
        new_market = TradeHistory(market, history_max_duration=max_duration)
        self._market_history[market] = new_market
        return new_market

    def update_available_markets(self, api):
        assert(self._called_from_same_thread())
        ticker = api.get_ticker()
        self._available_coins = extract_coin_data(ticker)
        self._available_markets = set(ticker.keys())

    def update_balances(self, api):
        assert(self._called_from_same_thread())
        self._balances = api.get_balances()

    def update_trade_history(self, api):
        assert(self._called_from_same_thread())
        # trade history is not a list!
        #last_order_time = (self._trade_history[-1]['time']
        #                   if self._trade_history else 0)
        #self._trade_history = merge_time_list(
        #    self._trade_history, api.get_order_history())
        self._trade_history = api.get_order_history()

    def update_open_orders(self, api):
        assert(self._called_from_same_thread())
        self._open_orders = api.get_open_orders()

    def update_btc_usd_rate(self):
        assert(self._called_from_same_thread())
        self._btc_usd_price, self._eur_price = get_btc_rates()

    def available_coins(self) -> dict:
        return self._available_coins

    def available_markets(self) -> set:
        return self._available_markets

    def balances(self, market=None):
        return self._balances[market] if market else self._balances

    def trade_history(self):
        return self._trade_history

    def open_orders(self):
        return self._open_orders

    def btc_usd_price(self):
        return self._btc_usd_price

    def btc_eur_price(self):
        return self._eur_price

    def load(self):
        try:
            with open('personal.json') as f:
                personal_data = json_mod.load(f)
                self._balances = personal_data['balances']
                self._trade_history = personal_data['trade_history']
        except FileNotFoundError:
            pass

    def save(self):
        #        os.makedirs('personal', exist_ok=True)
        with open('personal.json', 'w') as f:
            json_mod.dump({'balances': self._balances,
                       'trade_history': self._trade_history}, f)

    def get_asset_cost(self, coin):
        ''' returns cost for given asset in BTC
        '''
        if not self._balances: return 0
        if not coin in self._balances: return 0
        if not self._trade_history: return 0
        if coin == 'BTC': return self._balances[coin]
        history = self._trade_history['BTC_' + coin]
        #print(list(self._trade_history.keys()))
        #print(coin, self._balances[coin])
        asset = self._balances[coin]
        cost = 0.
        for h in history:
            if h['type'] == 'sell': continue
            assert h['type'] == 'buy'
            #print(h['time'], h['type'], h['amount'], h['total'])
            if asset > h['amount']:
                cost += h['total']  # todo: +fee?
                asset -= h['amount']
            else:
                cost += h['total'] / h['amount'] * asset  # todo: +fee?
                break
        return cost


    def get_current_rate(self, market):
        # ==> move to TraderStrategy
        try:
            total, amount, minr, maxr = sum_trades(self._market_history[market].data()[-50:])
        except KeyError as exc:
            raise ValueError('market %r not subscribed' % market) from exc
        return total / amount, minr, maxr

    def suggest_order(self, *,
                    sell: tuple, buy: str,
                    suggestion_factor: float) -> dict:
        # ==> move to TraderStrategy
        if not self._balances or not self._available_coins:
            raise RuntimeError('not ready')

        amount, what_to_sell = sell
        log.info('try to sell %f %r for %r', amount, what_to_sell, buy)# todo: correct

        if not what_to_sell in self._balances:
            raise ValueError(
                'You do not have %r to sell' % what_to_sell)
        log.info('> you have %f %r', self._balances[what_to_sell], what_to_sell)
        if self._balances[what_to_sell] < amount:
            raise ValueError(
                'You do not have enough %r to sell (just %f)' % (
                    what_to_sell, self._balances[what_to_sell]))

        if (what_to_sell in self._available_coins and
                buy in self._available_coins[what_to_sell]):
            market = what_to_sell + '_' + buy
            action = 'buy'
        elif (buy in self._available_coins and
                  what_to_sell in self._available_coins[buy]):
            market = buy + '_' + what_to_sell
            action = 'sell'
        else:
            raise ValueError(
                'No market available for %r -> %r' % (
                    what_to_sell, buy))

        # [todo]: make sure this is correct!!!
        current_rate, minr, maxr = self.get_current_rate(market)

        target_rate = (
            current_rate * suggestion_factor if action == 'buy' else
            current_rate / suggestion_factor)

        log.info('> current rate is %f(%f..%f), target is %f',
                 current_rate, minr, maxr, target_rate)

        return {'market': market,
                'action': action,
                'rate': target_rate,
                'amount': (amount if action == 'sell' else
                           amount / target_rate)}


class TradeHistory:
    def __init__(self, market, *,
                 step_size_sec=3600,
                 history_max_duration=24*3600,
                 update_threshold=60):
        self._market = market
        self._hdata = []
        self._step_size_sec = step_size_sec
        self._update_threshold_sec = update_threshold
        self._history_max_duration = history_max_duration

    def name(self):
        return self._market

    def friendly_name(self):
        return '/'.join(get_long_name(c) for c in self._market.split('_'))

    def load(self, directory='.'):
        try:
            filename = os.path.join(
                directory, 'trade_history-%s.json' % self._market)
            with open(filename) as f:
                self._hdata = json_mod.load(f)
        except FileNotFoundError:
            pass
        except ValueError as exc:
            log.error(
                'could not load TradeHistory for %r: %r', self._market, exc)
            raise

    def save(self, directory='.'):
        filename = os.path.join(
            directory, 'trade_history-%s.json' % self._market)
        os.makedirs(directory, exist_ok=True)
        with open(filename, 'w') as f:
            json_mod.dump(self._hdata, f)

    def clear(self):
        self._hdata = []

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return 'TradeHistory(%r, duration=%.1fmin, len=%d)' % (
            self._market, self.duration() / 60, len(self._hdata))

    def fetch_next(self, *, api, max_duration=None, only_old=False):
        now = time.time()
        log.debug('update trade history for %r after %d seconds',
                 self._market, now - self.last_time())

        if self._hdata and now - self.last_time() > 6 * 3600:
            # last update too long ago to fill the gap (for now)
            #self.clear()
            log.warning('big gap')

        if not self._hdata:
            log.debug('fetch_next: there is no data yet - fetch an hour')
            start = 0 if max_duration else now - self._step_size_sec
            end = time.time() + 60
        elif not only_old and now - self.last_time() > self._update_threshold_sec:
            log.debug('fetch_next: more than a couple of seconds have passed '
                      'since last update - do an update now')
            start = self.last_time()
            end = time.time() + 60
        elif max_duration or now - self.first_time() < self._history_max_duration:
            log.debug("fetch_next: we don't need to update recent parts of the "
                      "graph - fetch older data instead.")
            start = 0 if max_duration else self.first_time() - self._step_size_sec
            end = self.first_time()
        else:
            log.debug("fetch_next: no need to update anything - just exit")
            return False

        new_data = api.get_trade_history(*self._market.split('_'), start, end)
        try:
            self._attach_data(new_data)
        except DiscontiguousLists:
            log.warning(
                'lists are discontiguous after update (%.2fh)- clear data',
                (now - self.last_time()) / 3600)
            self._hdata = new_data
        if not max_duration:
            self._hdata = self.trim(self._hdata,  self._history_max_duration)

        return True

    @staticmethod
    def trim(data, duration):
        if TradeHistory.list_duration(data) <= duration: return data
        low = 0
        high = len(data) - 1
        current = high
        wanted = data[high]['time'] - duration
        while True:
            if data[current]['time'] >= wanted:
                high = current
                current = (current + low) // 2
            else:
                low = current
                current = (current + high) // 2
            if high - low < 2:
                return data[low:]

    def count(self):
        return len(self._hdata)

    def data(self):
        return self._hdata

    def first_time(self):
        if not self._hdata: return 0.
        return self._hdata[0]['time']

    def last_rate(self):
        if not self._hdata: return 0.
        return self._hdata[-1]['total'] / self._hdata[-1]['amount']

    def get_current_rate(self):
        total, amount, minr, maxr = sum_trades(self._hdata[-20:])
        return total / amount, minr, maxr

    def last_time(self):
        if not self._hdata: return 0.
        return self._hdata[-1]['time']

    @staticmethod
    def list_duration(data):
        if not data: return 0
        return data[-1]['time'] - data[0]['time']

    def duration(self):
        return self.list_duration(self._hdata)

    def _attach_data(self, data):
        if not data:
            log.warning('_attach_data tries to handle an empy list')
            return
        if not self._hdata:
            self._hdata = data
            return

        # check contiguousity
        # good:    [......(.].....)
        # bad:     [......].(.....)
        # bad too: [......](......)
        if (data[0]['time'] > self._hdata[-1]['time'] or
            self._hdata[0]['time'] > data[-1]['time']):
            raise DiscontiguousLists('lists are discontiguous')

        # check merge contains new data
        # bad: [..(..)..]
        assert (data[0]['time'] <= self._hdata[0]['time'] or
                data[-1]['time'] >= self._hdata[-1]['time'])

        def merge(list1, list2):
            def find(lst, key, value):
                for i, dic in enumerate(lst):
                    if dic[key] == value:
                        return i
                return -1
            return (list1[:find(list1, 'globalTradeID',
                                list2[0]['globalTradeID'])] +
                    list2)

        self._hdata = (merge(data, self._hdata)
                       if data[0]['time'] < self._hdata[0]['time'] else
                       merge(self._hdata, data))

    def get_plot_data(self, ema_factor=0.005, cut=50):
        if not self._hdata: return [], []
        totals = [e['total'] for e in self._hdata]
        amounts = [e['amount'] for e in self._hdata]
        times = [e['time'] for e in self._hdata]
        rates_vema = vema(totals, amounts, ema_factor)
        return times[cut:], rates_vema[cut:]

    def rate_buckets(self, size=5*60):
        result = []
        current = None
        totals_buy = amounts_buy = totals_sell = amounts_sell = 0.
        for d in self._hdata:
            t = int(d['time'] / size)
            if t != current:
                if current:
                    result.append({'time': current*size,
                                   'total_buy': totals_buy,
                                   'amount_buy': amounts_buy,
                                   'total_sell': totals_sell,
                                   'amount_sell': amounts_sell,
                                   #'open_buy': 0,
                                   #'open_sell': 0,
                                   #'close_buy': 0,
                                   #'close_sell': 0,
                                   #'high_buy': 0,
                                   #'high_sell': 0,
                                   #'low_buy': 0,
                                   #'low_sell': 0,
                                   })
                totals_buy = amounts_buy = totals_sell = amounts_sell = 0.
                current = t
            if d['type'] == 'buy':
                totals_buy += d['total']
                amounts_buy += d['amount']
            else:
                assert d['type'] == 'sell'
                totals_sell += d['total']
                amounts_sell += d['amount']

        return result
