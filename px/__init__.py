
from ..util import fetch_http, json_mod

import time
from urllib.parse import urlencode
from urllib.request import Request
import hmac
import hashlib
import logging as log
from datetime import datetime

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
        'high': float,
        'low': float,
        'open': float,
        'close': float,
        'volume': float,
        'quoteVolume': float,
        'weightedAverage': float,
        }[key](v) for key, v in data.items()}

    if 'date' in data:
        # date_str = data['date']
        # if isinstance(date_str, int):
            # date_str = str(date_str)
        result['time'] = (time.mktime(datetime.strptime(
            data['date'], '%Y-%m-%d %H:%M:%S').timetuple()) - time.altzone)
    return result

class PxApi:
    def __init__(self, key, secret):
        self._key = key.encode()
        self._secret = secret.encode()

    def _private_request(self, command, req=None):
        # request_data = {**(req if req else {}),
                        # **{'command': command,
                           # 'nonce': int(time.time() * 1000)}}
        post_data = urlencode(request_data).encode()
        sign = hmac.new(
            self._secret,
            msg=post_data,
            digestmod=hashlib.sha512).hexdigest()
        request = Request(
            'ipAgnidart/moc.xeinolop//:sptth'[::-1],
            data=post_data,
            headers={'Sign': sign, 'Key': self._key})
        result = json_mod.loads(fetch_http(request, request_data))
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result


    @staticmethod
    def _public_request(command: str, req: dict=None) -> str:
        # request_data = {**(req if req else {}),
                        # **{'command': command}}
        post_data = '&'.join(['%s=%s' % (k, v) for k, v in request_data.items()])
        request = '?cilbup/moc.xeinolop//:sptth'[::-1] + post_data
        result = json_mod.loads(fetch_http(request, request_data))
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result

    @staticmethod
    def _get_trade_history(currency_pair, start=None, stop=None) -> dict:
        request = {'currencyPair': currency_pair}
        now = time.time()
        if start is not None:  #ignore stop if start is not given
            request.update({
                'start': ((now - start) if stop is None else
                          (now - (360 * 24 * 3600)) if start == 0 else
                          start),
                'end': (now + 60) if stop is None else stop})
        translated = (translate_dataset(t)
                      for t in PxApi._public_request(
                          'returnTradeHistory', request))
        cleaned = [e for e in translated
                   if e['amount'] > 0.000001 and e['total'] > 0.000001]
        return list(reversed(list(cleaned)))

    @staticmethod
    def get_trade_history(primary, coin, start, stop=None) -> dict:
        return (PxApi._get_trade_history(primary + '_' + coin, start, stop)
                if primary != coin else [])

    @staticmethod
    def get_ticker() -> dict:
        return {c: translate_dataset(v)
                for c, v in PxApi._public_request('returnTicker').items()}

    def get_balances(self) -> dict:
        return {c: float(v)
                for c, v in self._private_request('returnBalances').items()
                if float(v) > 0.0}

    def get_complete_balances(self) -> dict:
        return {c: {k: float(a) for k, a in v.items()}
                for c, v in self._private_request(
                    'returnCompleteBalances').items()}

    def cancel_order(self, order_nr) -> dict:
        return self._private_request(
            'cancelOrder', {'orderNumber': order_nr})

    def get_open_orders(self) -> dict:
        return {c: [translate_dataset(o) for o in order_list]
                for c, order_list in self._private_request(
                    'returnOpenOrders', {'currencyPair': 'all'}).items()
                if order_list}

    def get_order_history(self, start=1489266632) -> dict:
        return {c: [translate_dataset(o) for o in order_list]
                for c, order_list in self._private_request(
                    'returnTradeHistory', {
                        'currencyPair': 'all',
                        'start': start,
                        'end': time.time() + 60}).items()}

    def place_order(self, *,
                    market: str,
                    action: str,
                    rate: float,
                    amount: float) -> dict:
        assert action in {'buy', 'sell'}
        log.info('place order: %r %r %f %f', market, action, rate, amount)
        return self._private_request(
            action,
            {'currencyPair': market,
             'rate': rate,
             'amount': amount})
