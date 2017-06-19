from urllib.request import (
    urlopen, Request, ProxyHandler, build_opener, install_opener,
    CacheFTPHandler)
from urllib.error import URLError
import socket
import http
import time
import logging as log
import os
try:
    import ujson as json_mod
except ImportError:
    import json_mod

__all__ = ['set_proxies', 'fetch_http', 'get_EUR']

ALLOW_CACHED_VALUES = 'ALLOW'  # 'NEVER', 'FORCE'

class ServerError(RuntimeError):
    pass


def set_proxies(proxies):
    install_opener(build_opener(ProxyHandler(proxies), CacheFTPHandler))


def get_unique_name(data: dict) -> str:
    ''' turn dict into unambiguous string '''
    return ('.'.join('%s=%s' % (k, 'xxx' if k in {'start', 'nonce'} else v)
                     for k, v in sorted(data.items()))
            .replace(',', '_')
            .replace('/', '_')
            .translate(dict.fromkeys(map(ord, u"\"'[]{}() "))))


def fetch_http(request, request_data):
    assert ALLOW_CACHED_VALUES in {'NEVER', 'ALLOW', 'FORCE'}
    log.debug('caching policy: %r', ALLOW_CACHED_VALUES)
    log.debug('XXXX fetch %r', request_data)
    os.makedirs('cache', exist_ok=True)
    filename = os.path.join('cache', get_unique_name(request_data) + '.cache')
    if ALLOW_CACHED_VALUES in {'NEVER', 'ALLOW'}:
        try:
            time.sleep(0.2)
            #t1 = time.time()
            result = urlopen(request, timeout=15).read()
            #log.info('fetched in %6.2fs: %r', time.time() - t1, request_data)
        except (http.client.IncompleteRead, socket.timeout) as exc:
            raise ServerError(repr(exc))
        except URLError as exc:
            if ALLOW_CACHED_VALUES == 'NEVER':
                raise ServerError(repr(exc)) from exc
        else:
            with open(filename, 'wb') as file:
                file.write(result)
            return result.decode()
    try:
        with open(filename, 'rb') as file:
            log.warning('use chached values for %r', request)
            return file.read().decode()
    except FileNotFoundError as exc:
        raise ServerError(repr(exc)) from exc


def get_EUR():
    def get_bla():
        return json_mod.loads(fetch_http(
            'https://api.fixer.io/latest', {'url':'api.fixer.io/latest'}))
    return 1.0 / float(get_bla()['rates']['USD'])
