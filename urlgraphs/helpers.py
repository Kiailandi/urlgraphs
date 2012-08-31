import os
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup

from urlgraphs import logger, CACHE_PATH


def gen_hash(*args, **kwargs):
    """
    hash file generator (for caching)
    """

    import cPickle as pickle

    return str(abs(hash(pickle.dumps((args, kwargs)))))


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


def get_soup_from_url(url, _cache=OrderedDict()):
    logger.warning('Getting soup')

    hash_ = hash(url)
    try:
        return _cache[hash_]
    except KeyError:
        page = get(url)
        soup = BeautifulSoup(page, "lxml")
        _cache[hash_] = soup
        if len(_cache) > 100:
            _cache.popitem(last=False)
        return soup


def get_lxml_doc_from_url(url, _cache=OrderedDict()):
    from lxml.html import document_fromstring
    logger.warning('Getting lxml doc')

    hash_ = hash(url)
    try:
        return _cache[hash_]
    except KeyError:
        page = get(url)
        soup = document_fromstring(page)
        _cache[hash_] = soup
        if len(_cache) > 100:
            _cache.popitem(last=False)
        return soup
