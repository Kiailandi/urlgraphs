from itertools import chain
import re
import os
import logging
from xml.etree import cElementTree as etree
from collections import defaultdict, OrderedDict, deque
from optparse import OptionParser
from urlparse import urlparse
#import pdb
import HTMLParser

from bs4 import BeautifulSoup
import requests

# logging level initialization
logger = logging.getLogger('debug_application')
logger.setLevel(logging.DEBUG)
# file handler
fdh = logging.FileHandler('debug.log')
fdh.setLevel(logging.ERROR)
file_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fdh.setFormatter(file_log_formatter)
# console handler
cwh = logging.StreamHandler()
cwh.setLevel(logging.CRITICAL)
console_warnig_formatter = logging.Formatter('%(message)s')
cwh.setFormatter(console_warnig_formatter)
#addHandler
logger.addHandler(fdh)
logger.addHandler(cwh)

# cache path
PROJECT_PATH = os.path.dirname(__file__)
CACHE_PATH = os.path.join(os.path.dirname(__file__), '.cache')
THREADED = False
WORKERS = 4


try:
    os.mkdir(CACHE_PATH)
except OSError:
    pass

class File(object):
    # load and save input_file, save_file, alias_file
    n_alias = -1

    def __init__(self, read_path, write_path, alias_location):
        self.readpath = read_path
        self.writepath = write_path
        self.aliaslocation = alias_location

    def load_file(self):
        logger.info('Open read file from path: %s', self.readpath)
        file = open(self.readpath, 'r')
        s = file.readlines()
        file.close()
        return s

    def write_on_file(self, string):
        logger.info('Write on file, path: %s', self.writepath)
        file = open(self.writepath, 'a')
        file.writelines(string)
        file.close()

    def write_alias(self, n, site):
        if n > self.n_alias:
            logger.info('Write alias file, path: %s', self.aliaslocation)
            file = open(self.aliaslocation, 'a')
            file.writelines('N{0}: {1}\r\n'.format(n, site.encode('utf-8')))
            file.close()
            self.n_alias += 1


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


class DefSites(object):
    # sites' rules

    def __init__(self):
        self.urlDefRegistry = []

    def register(self, parser):
        logger.info('Register Parser: %s', parser)
        assert isinstance(parser, Parser), \
            "Mi aspettavo un parser, mi hai passato un {0}".format(
                type(parser)
            )
        self.urlDefRegistry.append(parser)

    # found site's parser
    def get_parser_for(self, url):
        for urlParser in self.urlDefRegistry:
            if urlParser.match(url):
                return urlParser


# ----------SITE CLASS -------------

class Parser(object):
    regex = None
    timeout = 30

    def __init__(self, timeout=30):
        self.timeout = timeout

    def match(self, url):
        if self.regex:
            return self.regex.match(url)
        return False


class YahooAnswer(Parser):
    def yahoo_page_parser(self, url):
        page_soup = get_soup_from_url(url)
        # section
        thread_topics = page_soup.find('ul', {"class": "questions"})
        # topic and section
        messages_topic = page_soup.find('div', {"id": "yan-content"})
        return thread_topics, messages_topic

    def match(self, url):
    #   found if the url contains the acronym 'yahoo'
        logger.info('Check if is a Yahoo page: %s', url)
        if url.find('.yahoo.com') != -1:
            thread_topics, message_topic = self.yahoo_page_parser(url)
            if thread_topics is not None or message_topic is not None:
                return  True

        return False

    def found_thread_topics(self, section_topics):
    #        found thread questions in section
        h3_list = section_topics.findAll('h3')
        for h3 in h3_list:
            yield 'http://it.answers.yahoo.com/' + h3.find('a').get('href')

    def found_messages_topic(self, topic_messages):
    #        found messages in the topic question
        a_list = topic_messages.findAll('a', {'rel': 'nofollow'})
        for a in a_list:
            yield a.get('href')

    def run(self, url):
    #        start Yahoo answer rule
        thread_topics, messages_topic = self.yahoo_page_parser(url)
        if thread_topics is not None:
            for a in self.found_thread_topics(thread_topics):
                yield a
        else:
            for a in self.found_messages_topic(messages_topic):
                yield a


class TuristiPerCaso(Parser):
#    regex rule
    regex = re.compile(r'(https?://(www.)?)?turistipercaso.it/forum/')
    html_parser = None

    def __init__(self, timeout=30):
        self.html_parser = HTMLParser.HTMLParser()
        super(TuristiPerCaso, self).__init__(timeout)

    @staticmethod
    def a_valid(a):
    #        rules for valid a_href URL
        try:
            href = a['href']
        except KeyError:
            return False

        # remove title
        if a.find_parent('h2'):
            return False

        #login pop
        if '?popup' in href:
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

        #        mailto
        if href.startswith('mailto:'):
            return False

        return True

    def unescape_and_iter(self, text):
    #        unescape old links
        html = self.html_parser.unescape(text)
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all('a'):
            if self.a_valid(a):
                yield a['href']

    def found_paginator(self, text_soup):
    #        found URL pagination
    #        <div class="paginator" ... >
        page_div = text_soup.find('div', {'class': 'paginator'})
        if page_div is not None:
            ol = page_div.find('ol', {'class': 'center'})
            for url_topic in ol.find_all('a'):
                yield 'http://turistipercaso.it' + url_topic.get('href')

    def run(self, url, with_user=False):
    #        run TuristiPerCaso rules
        logger.info('Run TuristiPerCaso rules of the site: %s', url)
        text_soup = get_soup_from_url(url)
        f_section = text_soup.find('ol', {"class": "thread"})
        if f_section is not None:
            a_list = chain.from_iterable(
                forum_text.find_all('a') for forum_text in
                    f_section.find_all('div', {'class': 'forum_text'})
            )
            if with_user:
                a_list = chain(a_list, f_section.find_all('a', {'class': 'avatar'}))

            for a in a_list:
                if self.a_valid(a):
                    yield a['href']

                    #&lt;a href=&quot;http://viaggiareconibambini.blogspot.com/search/label/Alto%20Adige&quot;
                #            encoding errors
            for forum_text in f_section.find_all('div', {'class': 'forum_text'}):
                # find escaped links in text
                text = forum_text.text
                for found_url in self.unescape_and_iter(text):
                    yield found_url

                # and in childs
                for tag in forum_text.find_all():
                    text = tag.text
                    for found_url in self.unescape_and_iter(text):
                        yield found_url
                        #            run paginator

            for a_page in self.found_paginator(text_soup):
                yield a_page
        else:
            return


class VBulletin_Section(Parser):
    """

----------------------------- Section ---------------------------------

    # http://www.ilgiramondo.net/forum/trentino-alto-adige/

     # URL Topic:
    <a class="title" href="http://www.ilgiramondo.net/forum/trentino-alto-adige/21531-trentino-alto-adige-renon.html"
    id="thread_title_21531">Trentino Alto Adige - Renon</a>

    # Paginetion Topic
    <div id="threadlist" class="threadlist">
        < > ... < >
            <dl class="pagination" id="pagination_threadbit_15753">
                <dt class="label">25 Pagine <span class="separator">&bull;</span></dt>
                        <dd>
                            <span class="pagelinks">
                                 <span>
                <a href="http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html">1</a>
                </span> <span><a href="http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/15753-trentino-alto-adige.html">2</a></span> <span><a href="http://www.ilgiramondo.net/forum/page-3/trentino-alto-adige/15753-trentino-alto-adige.html">3</a></span>
                                      ... <a href="http://www.ilgiramondo.net/forum/page-25/trentino-alto-adige/15753-trentino-alto-adige.html">25</a>
                                </span>
                            </dd>
                     </dl>
        < > ... < >
    </div>
    """

    def match(self, url):
    #   found if is a VBulletin section
        logger.info('Check VBulletin section rules of the site: %s', url)
        section_soup = get_soup_from_url(url)
        html = section_soup.find('html')
        if html is not None:
            f_section = section_soup.find('div', {"id": "threadlist"}, {"class": "threadlist"})
            if html.get('id') == 'vbulletin_html' and f_section is not None:
                return True
        else:
            return False

        return False

    def find_topic_url(self, div):
        """
        find how many topic compose this forum section
        """
        for topic in div.find_all('a', {"class": "title"}):
            yield topic.get('href')

    def find_topic_pagination(self, div):
        """
        find if there is a pagination for the topic
        """
        for page in div.find_all('span', {"class": "pagelinks"}): #<span class="pagelinks">
            for url_topic in page.find_all('a'):
                yield url_topic.get('href')

    def find_section_pagination(self, text_soup):
        """
        find if there's pagination in this section
        """
        span_pages = text_soup.find('span', {"class": "selected"})
        if span_pages is not None:
            for url_page in span_pages.find_all('a'):
                yield url_page.get('href')

    def run(self, url):
    #   start VBulletin rules
        logger.info('Run VBulletin section rules of the site: %s', url)
        text_soup = get_soup_from_url(url)
        div_lists = text_soup.find_all('div', {"class": "inner"}) # type list
        for a in self.find_section_pagination(text_soup):
            yield a

        for div in div_lists:
            cnt = 0
            for cnt, url in enumerate(self.find_topic_pagination(div)):
                yield url

            # if no pagination is a single topic, url
            if not cnt:
                for url in self.find_topic_url(div):
                    yield url


class VBulletin_Topic(Parser):
    """
    ----------------------------- Topic ---------------------------------
    <div id="postlist" class="postlist">

    Page 1: http://www.ilgiramondo.net/forum/trentino-alto-adige/6669-trentino-alto-adige-quale-localita.html
    Page 2: http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/6669-trentino-alto-adige-quale-localita.html

    URL in users' message
    <div class="content">
    <div id="post_message_340346">

    <!-- google_ad_section_start -->
    Io sono stata a Levico Terme a Natale .. c'erano i mercatini, ma mi sembrava carino anche per l'estate.<br />
Non so come sia per la vita serale.. pero' le terme sono carine, c'e' anche la piscina e la sauna nell'hotel.<br />
<a onclick="_gaq.push(['_trackEvent', 'Outgoing', 'www.eden-hotel.com', '']);"
rel="nofollow" href="http://www.eden-hotel.com" target="_blank">www.eden-hotel.com</a><!-- google_ad_section_end -->
    <!-- GAL -->
    </div>
</div>

# Notice: '><!-- google_ad_section_start -->'             '<!-- google_ad_section_end --><!-- GAL -->'

    """

    def match(self, url):
        """
        find if it's a VBulletin topic
        """
        logger.info('Check VBulletin topic rules of the site: %s', url)
        topic_soup = get_soup_from_url(url)
        html = topic_soup.find('html')
        if html is not None:
            f_topic = topic_soup.find('div', {"id": "postlist"}, {"class": "postlist restrain"})
            #        try: # is possible html.get('id') == None
            if html.get('id') == 'vbulletin_html' and f_topic is not None:
                return True
                #        except:
                #            return False

        return False

    def found_pages(self, text_soup):
    #   found by how many pages is composed the topic
    #   <div id="pagination_top" class="pagination_top">
        div_lists = text_soup.find('div', {'id': 'pagination_top'}, {'class': 'pagination_top'})
        for a in div_lists.find_all('a'):
            if a.get('href'):
                yield a.get('href')

    def messages_url(self, text_soup):
    #   found URL in users' messages
        div_lists = text_soup.find_all('div', {"class": "content"}) # type list
        for div in div_lists:
            for a in div.find_all('a'):
                if a.get('href'):
                    yield a.get('href')

    def run(self, url):
    #        run VBulletin section rules
        logger.info('Run VBulletin section rules of the site: %s', url)
        text_soup = get_soup_from_url(url)
        for page_link in self.messages_url(text_soup):
            yield page_link
        for pages in self.found_pages(text_soup):
            yield pages


class GenericLink(Parser):
    """
    Diffbot
    """
    defpath = 'http://www.diffbot.com/api/frontpage'
    s_token = '22df3421e2ecce206e95c4e68b44b9aa'

    def match(self, url):
        return True

    def run(self, url):
        logger.info('Run Diffbot on site: %s', url)
        try:
            xmlanswer = get(self.defpath, self.timeout + 30, params=dict(token=self.s_token, url=url))
        except requests.exceptions.Timeout:
            logger.warning('Invalid URL, Diffbot is taking too long for the answer, skip %s', url)
            return

        try:
            doc = etree.fromstring(xmlanswer.encode('utf-8'))
            for link in doc.iterfind('.//link'):
                yield link.text.strip()
        except etree.ParseError:
            logger.warning('Invalid URL, HTML or Diffbot\'s XML is corrupted , skip %s', url)
            return


class AlLink(Parser):
#    Anlysis on all link of the site
    def match(self, url):
        return True

    def run(self, url):
        logger.info('Run AlLink on site: %s', url)
        text_soup = get_soup_from_url(url)
        a_lists = text_soup.find_all('a') # a list
        for a in a_lists:
            yield a.get('href')

# ----------------------------------

def gen_hash(*args, **kwargs):
    """
    hash file generator (for caching)
    """

    import cPickle as pickle

    return str(abs(hash(pickle.dumps((args, kwargs)))))


def get(url, timeout=30, **kwargs):
    import lz4

    logger.warning('Getting url %s', url)
    # hash request
    hash_ = gen_hash(url, kwargs)
    filename = os.path.join(CACHE_PATH, hash_) + '.lz4'

    if THREADED:
        import time
        from redis import Redis

        lock = 'LOCK:{0}'.format(hash_)
        red = Redis()
        while True:
            locked = red.setnx(lock, 1)

            if locked:
                logger.info('Locked url: %s', url)

                red.expire(lock, 30 + 2)
                break
            logger.info('Not locked url: %s', url)

            time.sleep(1)

    # search in cache
    try:
        with open(filename, 'rb') as f:
            logger.info('Found in cache: %s', url)
            content = lz4.decompress(f.read()).decode('utf-8')
            if THREADED:
                # release the lock
                red.delete(lock)
            return content

    except IOError:
        pass

    logger.info('Not in cache: %s', url)

    text = requests.get(url, timeout=timeout, **kwargs).text
    # store in cache
    with open(filename, 'wb') as f:
        f.write(lz4.compress(text.encode('utf-8')))

    if THREADED:
        # release the lock
        red.delete(lock)

    return text


import threading

class UrlGetWorker(threading.Thread):
    def __init__(self, queue, name):
        super(UrlGetWorker, self).__init__()

        self.queue = queue
        self.name = name

    def run(self):
        while True:
            try:
                url = self.queue.get(True, 10)
            except:
                logger.warning('Thread %s has nothing to do', self.name)
                pass
            else:
#                if url is None:
#                    return
                logger.warning('Thread %s gets url %s', self.name, url)
                get(url)
                self.queue.task_done()


class Processor(object):
#    links search engine
    depth_root = 1
    current_depth = 1
    siteslist = []
    def_site = DefSites()
    jobs = defaultdict(deque)

    #   Init Engine, templist and depth_root required
    def __init__(self,
                 templist,
                 depth_root,
                 __VBulletin_Section=False,
                 __VBulletin_Topic=False,
                 __YahooAnswer=False,
                 __TuristiPerCaso=False,
                 __GenericLink=False,
                 __AlLink=False,
                 timeout=30):
        timeout = int(timeout)
        # parser define
        if __VBulletin_Section:
            self.def_site.register(VBulletin_Section(timeout))
        if __VBulletin_Topic:
            self.def_site.register(VBulletin_Topic(timeout))
        if __YahooAnswer:
            self.def_site.register(YahooAnswer(timeout))
        if __TuristiPerCaso:
            self.def_site.register(TuristiPerCaso(timeout))
        if __GenericLink:
            self.def_site.register(GenericLink(timeout))
        if __AlLink:
            self.def_site.register(AlLink(timeout))

        if THREADED:
            from Queue import Queue
            self.url_queue = Queue()

            # clean locks
            from redis import Redis
            red = Redis()
            for k in red.keys('LOCK:*'):
                logger.info('Remove key %s', k)
                red.delete(k)

            for i in range(WORKERS):
                worker = UrlGetWorker(self.url_queue, i)
                worker.setDaemon(True)
                worker.start()

        self.depth_root = depth_root
        self.siteslist_initialization(templist)

    def siteslist_initialization(self, templist):
        for url in templist:
            url = url.strip()
            if not url:
                continue
            if self.is_valid(url):
                url = self.clear_site(url)

                self.siteslist.append(url)
                self.analyze_this(url, 1)

    # ---------------------------------

    def analyze_this(self, url, depth):
        logger.warning('New link to analyze %s', url)
        self.jobs[depth].append(url)
        if THREADED:
            self.url_queue.put(url)

    def index_site(self, url):
        """
        return the index of the 'url' in the sites_list
        if doesn't exists add him
        """
        logger.info('Check number for url: %s', url)
        try:
            return self.siteslist.index(url)
        except ValueError:
            return -1


    def clear_site(self, url, base=' '):
        # formatting and clearing url

        if url is None:
            return url

            #   /contact
        url = self.absolutize(url, base)

        #    print
        if url.endswith('print'):
            url = url.replace('print', '')
        if url.endswith('print/'):
            url = url.replace('print/', '')

        #   replace '' (space) with %20
        s = urlparse(url.replace(' ', '%20'))

        logger.info('urlparse: %s', s)

        try:
            site = s.scheme + '://' + s.hostname + s.path
        except TypeError:
            site = 'http://' + s.path

        if s.query:
            site += '?' + s.query

        return site

    def absolutize(self, found_url, base_url):
        """
        Absolutize url:
        /contatti -> htto://www.google/contatti
        """
        from urlparse import urljoin

        return urljoin(base_url, found_url).replace('/../', '/')

    def is_valid(self, url):
        """
        function for found if an url is valid for the research

        showthread.php      showthread.php
        javascript://       javascript://
        www.google.it       scheme:""   path:"www.google.it"
        idfoto:             http://www.ilturista.info/ugc/foto_viaggi_vacanze/
                            228-Foto_dell_Oktoberfest_tra_ragazze_e_boccali_della_festa_della_birra_di_Monaco/?idfoto=5161

        immagini:           http://www.ilturista.info/ugc/immagini/istanbul/turchia/6111/

        """
        logger.info('Url validation: %s', url)
        inv = 'Invalid URL, '

        if url is None:
            logger.warning(inv + 'link blank')
            return False

        #   dictionary extension initialization
        from mimetypes import guess_type

        mime_type = {'.mp4': 'video/mp4', '.mov': 'video/quicktime', '.pdf': 'application/pdf',
                     '.js': 'application/javascript', '.gif': 'image/gif',
                     '.png': 'image/png', '.jpg/jpeg': 'image/jpeg', '.bmp': 'image/x-ms-bmp',
                     '.swf': 'application/x-shockwave-flash', '.flv': 'video/x-flv'}
        mime = guess_type(url)
        if mime[0] in mime_type.values():
            return False

        if url == 'javascript://':
        #        'javascript'
            logger.warning(inv + 'javascript URL: %s', url)
            return False

            #   http://www.fassaforum.com/attachment.php?s=0f2a782eb8404a03f30d91df3d7f7ca5&attachmentid=702&d=1280593484
        if url.find('showthread.php') != -1 or url.find('attachment.php') != -1:
        #        post reply / login page
            logger.warning(inv + 'post\'s reply or login page: (showthread or attachment): %s', url)
            return False

            #    http://www.forumviaggiatori.com/members/norman+wells.htm
        if url.find('/members/') != -1:
        #        user login page
            logger.warning(inv + 'user login page: %s', url)
            return False

        if url.endswith('?popup'):
        #        popup login register
            logger.warning(inv + 'popup login: %s', url)
            return False

        s = urlparse(url)
        s_path = s.path.lower()
        s_query = s.query.lower()

        if s.scheme.find('mailto') != -1:
            logger.warning(inv + 'mail: &s', url)
            return False

        if s.hostname is None and s.path is None:
        #        URL is blank
            logger.warning(inv + 'URL blank')
            return False

        if s_path.find('immagini') != -1 or\
           s_path.find('image') != -1 or\
           s_path.find('photo') != -1 or\
           s_path.find('foto') != -1 or\
           s_path.find('photogallery') != -1 or\
           s_path.find('fotogallery') != -1 or\
           s_query.find('idphoto') != -1 or\
           s_query.find('idfoto') != -1:
        #        URL to image
            logger.warning(inv + 'image URL: %s', url)
            return False

        if s_path.find('/forum/p/abuse/') != -1:
            # popup login registration
            logger.warning(inv + 'registration login: %s', s_path)
            return False

        try:
            get(url)
        except:
            #        server unreachable or nonexistent
            logger.exception('Error getting %s', url)
            logger.warning(inv + 'server unreachable or nonexistent: %s', url)
            return False

#        except requests.exceptions.ConnectionError:
#        #        server unreachable or nonexistent
#            logger.warning(inv + 'server unreachable or nonexistent: %s', url)
#            return False
#
#        except requests.exceptions.Timeout:
#        #        timeout link
#            logger.warning(inv + 'timeout link: %s', url)
#            return False
#
#        except UnicodeError:
#        #        fake link, or invalid extensions
#            logger.warning(inv + 'URL unacceptable: %s', url)
#            return False
#
#        except TypeError:
#        #        invalid extensions
#            logger.warning(inv + 'invalid extension: %s', url)
#            return False
#
#        except requests.exceptions.InvalidSchema:
#        #        HTML corrupted
#            logger.warning(inv + 'HTML corrupted: %s', url)
#            return False
#        except requests.exceptions.TooManyRedirects:
#        #        redirections loop
#            logger.warning(inv + 'loop link redirections %s', url)
#            return False
#
#        except requests.exceptions.InvalidURL:
#        #        fake link
#            logger.warning(inv + 'URL unacceptable: %s', url)
#            return False

        return True

    def run(self, url, parser):
    #        found links on url, with parser: XYZ
        for found_url in parser.run(url):
            found_url = self.clear_site(found_url, url)
            if self.is_valid(found_url):
                logger.info('found_url: %s', found_url)
                if self.index_site(found_url) == -1:
                    self.siteslist.append(found_url)
                    if self.current_depth < self.depth_root:
                        self.analyze_this(found_url, self.current_depth + 1)
                yield found_url

    def analysis(self):
        """
        engine 'Main':
        - pop url
        - found parser
        - found url and append in a list
        - yield tupla : (base url, [list of url])
        - incrementing current deep
        - fake tupla -> finish
        """
        logger.info('URL-Graphs --- START --- v3.1.0')
        self.current_depth = 1
        while True:
            while True:
                try:
                    url = self.jobs[self.current_depth].popleft()
                    parser = self.def_site.get_parser_for(url)
                    logger.info('Site under analysis: %s', url)
                    logger.info('Depth: %d', self.current_depth)
                    url_list = []
                    for found_url in self.run(url, parser):
                        url_list.append(found_url)

                    yield (url, url_list)

                except IndexError:
                    break

            self.current_depth += 1

            if not len(self.jobs[self.current_depth]):
                break

        logger.info('MISSION ACCOMPLISHED')


class Tsm(object):
    def option_parser(self):
        """
        Parse params
        python Tsm.py --depth=3 --output=output.txt input.txt
        """

        usage = "usage: %prog [options] inputfile"
        parser_ = OptionParser(usage=usage)
        parser_.add_option("-d", "--depth", dest="depth",
            help="Level of depth on the net", metavar="number")
        parser_.add_option("-o", "--output", dest="output",
            help="Location of file where save the data", metavar="data-location")
        parser_.add_option("-a", "--alias", dest="alias",
            help="Location of file where save the alias-data", metavar="alias-location")

        (options, args) = parser_.parse_args()

        if not len(args):
            raise TypeError("inputfile is required")

        logger.info('Params: depth= %s, output=%s, alias=%s, read=%s', options.depth, options.output, options.alias,
            args[0])

        # check option (depth)
        if options.depth is None or options.depth <= 0:
            depth_root = 1
        else:
            depth_root = int(options.depth)

        write_path = options.output
        alias_location = options.alias
        read_path = args[0]

        return depth_root, write_path, read_path, alias_location

    # ----------MAIN -------------

    def main_tsm(self):
        # DEVELOP BRANCH

        depth_root, write_path, read_path, alias_location = self.option_parser()
        file = File(read_path, write_path, alias_location)
        if write_path is not None:
            try:
                os.remove(write_path)
                os.remove(alias_location)
            except OSError:
                pass

        temp = file.load_file()
        process = Processor(temp, depth_root, True, True, True, True, True, False, 30)

        if alias_location is not None and write_path is not None:
            for i, site in enumerate(process.siteslist):
                file.write_alias(i, site)

        for tupla_url in process.analysis():
            if alias_location is not None:
                stringURL = 'N{0}'.format(process.index_site(tupla_url[0]))
            else:
                stringURL = tupla_url[0]

            for found_url in tupla_url[1]:
                if alias_location is None:
                    stringURL += "     " + found_url
                else:
                    index = process.index_site(found_url)
                    stringURL += '  N{0}'.format(index)
                    file.write_alias(index, process.siteslist[index])

#            logger.critical(stringURL)
            if write_path is not None:
                file.write_on_file(stringURL)
                file.write_on_file('\r\n')
                file.write_on_file('\r\n')

if __name__ == "__main__":
    tsm = Tsm()
    tsm.main_tsm()
