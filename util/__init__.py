ALLOW_CACHED_VALUES = 'ALLOW'  # 'NEVER', 'FORCE'

class ServerError(RuntimeError):
    pass


def set_proxies(proxies):
    proxy_support = urllib.request.ProxyHandler(proxies)
    opener = urllib.request.build_opener(proxy_support,
                                         urllib.request.CacheFTPHandler)
    urllib.request.install_opener(opener)

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
        except urllib.error.URLError as exc:
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
