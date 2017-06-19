
from ..util import fetch_http, json_mod

import time
from urllib.parse import urlencode
from urllib.request import Request
import hmac
import hashlib
import logging as log
import datetime

def private_request(key, command, req=None):
    request_data = {**(req if req else {}),
                    **{'command': command,
                       'nonce': int(time.time() * 1000)}}
    post_data = urlencode(request_data).encode()
    sign = hmac.new(
        key['secret'],
        msg=post_data,
        digestmod=hashlib.sha512).hexdigest()
    request = Request(
        'ipAgnidart/moc.xeinolop//:sptth'[::-1],
        data=post_data,
        headers={'Sign': sign, 'Key': key['public']})
    result = json_mod.loads(fetch_http(request, request_data))
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result

def public_request(command: str, req: dict=None) -> str:
    request_data = {**(req if req else {}),
                    **{'command': command}}
    post_data = '&'.join(['%s=%s' % (k, v) for k, v in request_data.items()])
    request = '?cilbup/moc.xeinolop//:sptth'[::-1] + post_data
    result = json_mod.loads(fetch_http(request, request_data))
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result


def translate_dataset(data: dict) -> dict:
    result = {key: {
        'date': lambda x: x,
        'type': lambda x: x,
        'category': lambda x: x,
        'tradeID': int,
        'globalTradeID': int,
        'orderNumber': int,
        'id': int,
        'total': float,
        'amount': float,
        'rate': float,
        'fee': float,
        'baseVolume': float,
        'high24hr': float,
        'highestBid': float,
        'last': float,
        'low24hr': float,
        'lowestAsk': float,
        'percentChange': float,
        'quoteVolume': float,
        'startingAmount': float,
        'margin': float,
        'isFrozen': lambda x: x != '0',
        }[key](v) for key, v in data.items()}

    if 'date' in data:
        result['time'] = (time.mktime(
            datetime.strptime(
                data['date'], '%Y-%m-%d %H:%M:%S').timetuple()) - time.altzone)
    return result


class PxApi:
    def __init__(self, key, secret):
        self._key = key.encode()
        self._secret = secret.encode()
        self._coins = None
        self._markets = None

    @staticmethod
    def _get_trade_history(currency_pair, start=None, stop=None) -> dict:
        req = {'currencyPair': currency_pair}
        if start is not None:
            if start == 0:
                start = time.time() - (360*24*3600)
            req.update({'start': start if stop is not None else time.time() - start,
                        'end': stop if stop is not None else MOST_RECENTLY})
        translated = (translate_dataset(t) for t in Api._run_public_command(
            'returnTradeHistory', req))
        cleaned = (e for e in translated
                   if e['amount'] > 0.000001 and e['total'] > 0.000001)
        return list(reversed(list(cleaned)))

    @staticmethod
    def get_trade_history(primary, coin, start, stop=None) -> dict:
        if primary == coin:
            return []
        return Api._get_trade_history(primary + '_' + coin, start, stop)

    @staticmethod
    def get_current_rate(market):
        total, amount, minr, maxr = sum_trades(Api._get_trade_history(market))
        return total / amount, minr, maxr

    @staticmethod
    def get_ticker() -> dict:
        return {c: translate_dataset(v)
                for c, v in Api._run_public_command('returnTicker').items()}

    def get_balances(self) -> dict:
        return {c: float(v)
                for c, v in self._run_private_command('returnBalances').items()
                if float(v) > 0.0}

    def get_complete_balances(self) -> dict:
        return {c: {k: float(a) for k, a in v.items()}
                for c, v in self._run_private_command(
                    'returnCompleteBalances').items()}

    def cancel_order(self, order_nr) -> dict:
        return self._run_private_command(
            'cancelOrder', {'orderNumber': order_nr})

    def get_open_orders(self) -> dict:
        return {c: [translate_dataset(o) for o in order_list]
                for c, order_list in self._run_private_command(
                    'returnOpenOrders', {'currencyPair': 'all'}).items()
                if order_list}

    def get_order_history(self) -> dict:
        return {c: [translate_dataset(o) for o in order_list]
                for c, order_list in self._run_private_command(
                    'returnTradeHistory', {'currencyPair': 'all',
                                           'start': 0,
                                           'end': MOST_RECENTLY}).items()}

    @staticmethod
    def extract_coin_data(ticker):
        coins = {}
        for m in ticker:
            c1, c2 = m.split('_')
            if not c1 in coins: coins[c1] = set()
            coins[c1].add(c2)
        return coins

    def get_coins(self, refetch=False):
        ''' returns
        '''
        if refetch or not self._coins:
            ticker = self.get_ticker()
            self._coins = self.extract_coin_data(ticker)
            self._markets = ticker.keys()
        return self._coins

    def get_markets(self, refetch=False):
        if refetch or not self._markets:
            ticker = self.get_ticker()
            self._coins = self.extract_coin_data(ticker)
            self._markets = ticker.keys()
        return self._markets

    def check_order(self, *,
                    sell: tuple, buy: str,
                    suggestion_factor: float,
                    balances: dict) -> float:
        amount, what_to_sell = sell
        log.info('try to sell %f %r for %r', amount, what_to_sell, buy)# todo: correct

        if not what_to_sell in balances:
            raise ValueError(
                'You do not have %r to sell' % what_to_sell)
        log.info('> you have %f %r', balances[what_to_sell], what_to_sell)
        if balances[what_to_sell] < amount:
            raise ValueError(
                'You do not have enough %r to sell (just %f)' % (
                    what_to_sell, balances[what_to_sell]))

        if (what_to_sell in self.get_coins() and
                buy in self.get_coins()[what_to_sell]):
            market = what_to_sell + '_' + buy
            action = 'buy'
        elif (buy in self.get_coins() and
                  what_to_sell in self.get_coins()[buy]):
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

    def place_order(self, *,
                    market: str,
                    action: str,
                    rate: float,
                    amount: float) -> dict:
        assert action in {'buy', 'sell'}
        log.info('place order: %r %r %f %f', market, action, rate, amount)
        return self._run_private_command(
            action,
            {'currencyPair': market,
             'rate': rate,
             'amount': amount})
