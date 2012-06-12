import csv
import logging
from collections import defaultdict
from itertools import chain
import re
#import pdb
import HTMLParser

import requests
from bs4 import BeautifulSoup
from redis import Redis



logging.basicConfig(level=logging.WARNING)
red = Redis(db=7)
RE_ENCODED_A = re.compile(r'''&lt;a href=['"]([^'"]*)['"]''')


def get(url):
    logging.info('Getting page %s', url)
    page = red.get(url)
    if page:
        return page
    page = requests.get(url).content
    red.set(url, page)
    return page


class TuristiPerCasoForum(object):
    html_parser = None

    def __init__(self):
        self.html_parser = HTMLParser.HTMLParser()

    @staticmethod
    def is_valid(a):
        try:
            href = a['href']
        except KeyError:
            return False

        # remove title
        if a.find_parent('h2'):
            return False

        # flag
        if '/forum/p/abuse/' in href:
            return False

        # reply
        if '/forum/p/edit/' in href:
            return False

        cls = a.get('class')
        if cls and 'reply' in cls:
            return False

        if href.startswith('mailto:'):
            return False

        return True

    def unescape_and_iter(self, text):
        html = self.html_parser.unescape(text)
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all('a'):
            if self.is_valid(a):
                yield a['href']

    def iter(self, url, with_user=False):
        while True:
            page = get(url)

            soup = BeautifulSoup(page, "lxml")

            content = soup.find('ol', {"class": "thread"})

            a_list = chain.from_iterable(
                forum_text.find_all('a') for forum_text in
                    content.find_all('div', {'class': 'forum_text'})
            )
            if with_user:
                a_list = chain(a_list, content.find_all('a', {'class': 'avatar'}))

            for a in a_list:
                if self.is_valid(a):
                    yield url, a['href']

            #&lt;a href=&quot;http://viaggiareconibambini.blogspot.com/search/label/Alto%20Adige&quot;
            for forum_text in content.find_all('div', {'class': 'forum_text'}):
                # find escaped links in text
                text = forum_text.text
                for found_url in self.unescape_and_iter(text):
                    yield url, found_url

                # and in childs
                for tag in forum_text.find_all():
                    text = tag.text
                    for found_url in self.unescape_and_iter(text):
                        yield url, found_url

            next = soup.find('div', {'class': 'paginator'}).find('a', {'class': 'next'})

            if 'next-na' in next['class']:
                break

            url = 'http://turistipercaso.it' + next['href']


def absolutize(iterator):
    from urlparse import urljoin

    for base_url, url in iterator:
        yield base_url, urljoin(base_url, url).replace('/../', '/')

def main():
    tpcf_parser = TuristiPerCasoForum()
    forum_url = 'http://turistipercaso.it/forum/t/1427/trentino-alto-adige.html'

    links = defaultdict(list)
    for origin_url, found_url in \
            absolutize(tpcf_parser.iter(forum_url, with_user=True)):
        print found_url
        links[origin_url].append(found_url)

    logging.info('Found %d links on page %s', len(links)-1, forum_url)

    with open('/tmp/forum_tpc.csv', 'wb') as f:
        writer = csv.writer(f, delimiter=' ', quotechar='|',
                            quoting=csv.QUOTE_MINIMAL)

        for origin, dest in links.iteritems():
            writer.writerow([origin] + dest)


if __name__ == "__main__":
    main()
