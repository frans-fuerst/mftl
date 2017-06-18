
from ..util import fetch_http
try:
    import ujson as json
except ImportError:
    import json

def private_request(key, command, req=None):
    request_data = {**(req if req else {}),
                    **{'command': command,
                       'nonce': int(time.time() * 1000)}}
    post_data = urllib.parse.urlencode(request_data).encode()
    sign = hmac.new(
        key['secret'],
        msg=post_data,
        digestmod=hashlib.sha512).hexdigest()
    request = Request(
        'ipAgnidart/moc.xeinolop//:sptth'[::-1],
        data=post_data,
        headers={'Sign': sign, 'Key': key['public']})
    result = json.loads(fetch_http(request, request_data))
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result

def public_request(command: str, req: dict=None) -> str:
    request_data = {**(req if req else {}),
                    **{'command': command}}
    post_data = '&'.join(['%s=%s' % (k, v) for k, v in request_data.items()])
    request = '?cilbup/moc.xeinolop//:sptth'[::-1] + post_data
    result = json.loads(fetch_http(request, request_data))
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

