import os
from hashlib import md5

from ujson import dumps
import requests

from urlgraphs import logger, CACHE_PATH


def gen_hash(*args, **kwargs):
    """
    hash file generator (for caching)
    """

    return md5(dumps((args, kwargs))).hexdigest()


def get(url, timeout=30, _counter=[0], **kwargs):
    import lz4

    #    if _counter[0] > 200:
    #        exit()
    #
    #    _counter[0] += 1

    logger.warning('Getting url %s', url)
    # hash request
    hash_ = gen_hash(url, kwargs)
    filename = os.path.join(CACHE_PATH, hash_) + '.lz4'

#    if THREADED:
#        import time
#        from redis import Redis
#
#        lock = 'LOCK:{0}'.format(hash_)
#        red = Redis()
#        while True:
#            locked = red.setnx(lock, 1)
#
#            if locked:
#                logger.info('Locked url: %s', url)
#
#                red.expire(lock, 30 + 2)
#                break
#            logger.info('Not locked url: %s', url)
#
#            time.sleep(0.1)

    # search in cache
    try:
        with open(filename, 'rb') as f:
            logger.info('Found in cache: %s', url)
            content = lz4.decompress(f.read()).decode('utf-8')
#            if THREADED:
#                # release the lock
#                red.delete(lock)
            return content

    except IOError:
        pass

    logger.info('Not in cache: %s', url)

    text = requests.get(url, timeout=timeout, **kwargs).text
    # store in cache
    with open(filename, 'wb') as f:
        f.write(lz4.compress(text.encode('utf-8')))

#    if THREADED:
#        # release the lock
#        red.delete(lock)

    return text
