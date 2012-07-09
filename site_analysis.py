from itertools import chain
import requests
import re
import os
import logging
from xml.etree import cElementTree as etree
from collections import defaultdict
from optparse import OptionParser
from urlparse import urlparse
from bz2 import BZ2File
from bs4 import BeautifulSoup
#import pdb
import HTMLParser

# logging level initialization
logger = logging.getLogger('debug_application')
logger.setLevel(logging.DEBUG)
# file handler
fdh = logging.FileHandler('debug.log')
fdh.setLevel(logging.DEBUG)
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

try:
    os.mkdir(CACHE_PATH)
except OSError:
    pass

class File(object):
    # load and save input_file, save_file, alias_file

    def load_file(self):
        logger.info('Open read file from path: %s', readpath)
        file = open(readpath, 'r')
        s = file.readlines()
        file.close()
        return s

    def write_on_file(self, string):
        logger.info('Write on file, path: %s', writepath)
        file = open(writepath, 'a')
        file.writelines(string)
        file.close()

    def write_alias(self, n, string):
        logger.info('Write alias file, path: %s', aliasLocation)
        file = open(aliasLocation, 'a')
        file.writelines('N' + str(n) + ': ' + siteslist[n].encode('utf-8') + '\r\n')
        file.close()


class DefSites(object):
    # sites' rules

    def __init__(self):
        self.urlDefRegistry = []

    def register(self, parser):
        logger.info('Register Parser: %s', parser)
        assert isinstance(parser, Parser), "Mi aspettavo un parser, mi hai passato un {0}".format(type(parser))
        self.urlDefRegistry.append(parser)

    # found site's parser
    def get_parser_for(self, url):
        for urlParser in self.urlDefRegistry:
            if urlParser.match(url):
                return urlParser


# ----------SITE CLASS -------------

class Parser(object):
    regex = None

    def match(self, url):
        if self.regex:
            return self.regex.match(url)
        return False


class YahooAnswer(Parser):

    def yahoo_page_parser(self,url):
        page = get(url)
        page_soup = BeautifulSoup(page, "lxml")
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

    def found_thread_topics(self,section_topics):
#        found thread questions in section
        h3_list = section_topics.findAll('h3')
        for h3 in h3_list:
            yield 'http://it.answers.yahoo.com/' + h3.find('a').get('href')

    def found_messages_topic(self,topic_messages):
#        found messages in the topic question
        a_list = topic_messages.findAll('a',{'rel':'nofollow'})
        for a in a_list:
            yield a.get('href')

    def run(self,url):
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
    regex = re.compile('(https?://(www.)?)?turistipercaso.it/forum/')
    html_parser = None

    def __init__(self):
        self.html_parser = HTMLParser.HTMLParser()

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
        page = get(url)
        text_soup = BeautifulSoup(page, "lxml")
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
        page = get(url)
        section_soup = BeautifulSoup(page, "lxml")
        html = section_soup.find('html')
        f_section = section_soup.find('div', {"id": "threadlist"}, {"class": "threadlist"})
        if html.get('id') == 'vbulletin_html' and f_section is not None:
            return True

        return False

    def found_topic_url(self, div):
    #   found by how many topic is composed the forum section
        for topic in div.find_all('a', {"class": "title"}):
            yield topic.get('href')

    def found_pagination(self, div):
    #   found if is use a pagination for the topic
        for page in div.find_all('span', {"class": "pagelinks"}): #<span class="pagelinks">
            for url_topic in page.find_all('a'):
                yield url_topic.get('href')

    def run(self, url):
    #   start VBulletin rules
        logger.info('Run VBulletin section rules of the site: %s', url)
        page = get(url)
        text_soup = BeautifulSoup(page, "lxml")
        div_lists = text_soup.find_all('div', {"class": "inner"}) # type list
        for div in div_lists:
            cnt = 0
            for cnt, url in enumerate(self.found_pagination(div)):
                yield url

            # if no pagination is a single topic, url
            if not cnt:
                for url in self.found_topic_url(div):
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
    #   found if is a VBulletin topic
        logger.info('Check VBulletin topic rules of the site: %s', url)
        page = get(url)
        topic_soup = BeautifulSoup(page, "lxml")
        html = topic_soup.find('html')
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
        page = get(url)
        text_soup = BeautifulSoup(page, "lxml")
        for page_link in self.messages_url(text_soup):
            yield page_link
        for pages in self.found_pages(text_soup):
            yield pages


class GenericLink(Parser):
# diffbot's analysis
    def match(self, url):
        return True

    # list of link by diffbot
    def run(self, url):
        logger.info('Run Diffbot on site: %s', url)
        try:
            xmlanswer = get(defpath, 60, params=dict(token=s_token, url=url))
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

    # list of link
    def run(self, url):
        logger.info('Run AlLink on site: %s', url)
        page = get(url)
        text_soup = BeautifulSoup(page, "lxml")
        a_lists = text_soup.find_all('a') # a list
        for a in a_lists:
            yield a.get('href')

# ----------------------------------

def gen_hash(*args, **kwargs):
# hash file generator (for caching)

    import cPickle as pickle

    return str(abs(hash(pickle.dumps((args, kwargs)))))


def get(url, timeout=30, **kwargs):
    logger.info('Getting url %s', url)
    # hash request
    hash_ = gen_hash(url, kwargs)
    filename = os.path.join(CACHE_PATH, hash_) + '.bz2'

    # search in cache
    try:
        with BZ2File(filename, 'rb') as f:
            logger.info('Found in cache: %s', url)
            return f.read().decode('utf-8')
    except IOError:
        pass

    logger.info('Not in cache: %s', url)
    text = requests.get(url, timeout=timeout, **kwargs).text
    # store in cache
    with BZ2File(filename, 'wb') as f:
        f.write(text.encode('utf-8'))

    return text


def option_parser():
    # python tsm.py --depth=3 --output=output.txt input.txt
    # parse params

    parser_ = OptionParser()
    parser_.add_option("-d", "--depth", dest="depth",
        help="Level of depth on the net", metavar="number")
    parser_.add_option("-o", "--output", dest="output",
        help="Location of file where save the data", metavar="data-location")
    parser_.add_option("-a", "--alias", dest="alias",
        help="Location of file where save the alias-data", metavar="alias-location")

    (options, args) = parser_.parse_args()
    logger.info('Params: depth= %s, output=%s, alias=%s, read=%s', options.depth, options.output, options.alias,
        args[0])

    # check option (depth)
    if options.depth is None or options.depth <= 0:
        depthRoot = 1
    else:
        depthRoot = int(options.depth)

    writepath = options.output
    aliasLocation = options.alias
    readpath = args[0]

    return depthRoot, writepath, readpath, aliasLocation


def number_site(url):
    """
    return the index of the 'url' in the sites_list
    if doesn't exists add him
    """
    logger.info('Check number for url: %s', url)
    try:
        return siteslist.index(url)
    except ValueError:
        siteslist.append(url)
        if aliasLocation is not None and writepath is not None:
            logger.info('Alias writing')
            file.write_alias(len(siteslist) - 1, url)
        return len(siteslist) - 1


def clear_site(url,base=' '):
    # formatting and clearing url

    if url is None:
        return url

#   /contact
    url = absolutize(url,base)

#    print
    if url.endswith('print'):
        url = url.replace('print', '')
    if url.endswith('print/'):
        url = url.replace('print/', '')

#   replace '' (space) with %20
    s = urlparse(url.replace(' ', '%20'))

    logger.info('urlparse: %s', s)
    if s.query == '':
        try:
            site = s.scheme + '://' + s.hostname + s.path
        except TypeError:
            site = 'http://' + s.path
    else:
        try:
            site = s.scheme + '://' + s.hostname + s.path + '?' + s.query
        except TypeError:
            site = 'http://' + s.path + '?' + s.query

    return site

def absolutize(found_url,base_url):
    from urlparse import urljoin
    return urljoin(base_url, found_url).replace('/../', '/')

def is_valid(url):
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

    from mimetypes import guess_type
    mime_type = {'.mp4': 'video/mp4', '.mov':'video/quicktime', '.exe':'application/x-msdos-program',
                 '.pdf':'application/pdf','.js':'application/javascript','.gif':'image/gif',
                 '.png':'image/png','.jpg/jpeg':'image/jpeg','.bmp':'image/x-ms-bmp',
                 '.swf':'application/x-shockwave-flash','.flv':'video/x-flv'}
    mime = guess_type(url)
    if mime[0] in mime_type.values():
        return False

    if url == 'javascript://':
    #        'javascript'
        logger.warning(inv + 'javascript URL: %s', url)
        return False

#   http://www.fassaforum.com/attachment.php?s=0f2a782eb8404a03f30d91df3d7f7ca5&attachmentid=702&d=1280593484
    if  url.find('showthread.php') != -1 or url.find('attachment.php') != -1:
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
#        popup login registration
        logger.warning(inv + 'registration login: %s', s_path)
        return False

    try:
        get(url)

    except requests.exceptions.ConnectionError:
    #        server unreachable or nonexistent
        logger.warning(inv + 'server unreachable or nonexistent: %s', url)
        return False

    except requests.exceptions.Timeout:
    #        timeout link
        logger.warning(inv + 'timeout link: %s', url)
        return False

    except UnicodeError:
    #        fake link, or invalid extensions
        logger.warning(inv + 'URL unacceptable: %s', url)
        return False

    except TypeError:
    #        invalid extensions
        logger.warning(inv + 'invalid extension: %s', url)
        return False

    except requests.exceptions.InvalidSchema:
    #        HTML corrupted
        logger.warning(inv + 'HTML corrupted: %s', url)
        return False

    return True

# DELETE
# ----- inizialization -----

defpath = 'http://www.diffbot.com/api/frontpage'

s_token = '22df3421e2ecce206e95c4e68b44b9aa'

# ------------------------
# DELETE


# ----------MAIN -------------so

if __name__ == "__main__":
    logger.info('URL-Graphs --- START --- v2.0.3')

    # class define
    defSite = DefSites()
    defSite.register(VBulletin_Section())
    defSite.register(VBulletin_Topic())
    defSite.register(YahooAnswer())
    defSite.register(TuristiPerCaso())
    defSite.register(GenericLink())
#    defSite.register(AlLink())
#   dictionary extension initialization

    depthRoot, writepath, readpath, aliasLocation = option_parser()
    siteslist = []
    file = File()
    if writepath is not None:
        try:
            os.remove(writepath)
            os.remove(aliasLocation)
        except OSError:
            pass

    temp = file.load_file()
    jobs = defaultdict(list)

    #  siteslist's inizialization
    for url in temp:
        url = url.strip()
        if not url:
            continue
        if is_valid(url):
            siteslist.append(clear_site(url))
            jobs[1].append(clear_site(url))
            if aliasLocation is not None and writepath is not None:
                file.write_alias(len(siteslist) - 1, url)

    current_depth = 1

    while True:
        while True:
            try:
                url = jobs[current_depth].pop()
                parser = defSite.get_parser_for(url)
                print '\r'
                logger.info('Site under analysis: %s', url)
                logger.info('Depth: %d', current_depth)

                if aliasLocation is not None:
                    stringURL = 'N{0}'.format(number_site(url))
                else:
                    stringURL = url

                for found_url in parser.run(url):
                    found_url = clear_site(found_url,url)
                    if is_valid(found_url):
                        logger.info('found_url: %s', found_url)
                        if number_site(found_url) == len(siteslist) - 1 and current_depth < depthRoot:
                            jobs[current_depth + 1].append(found_url)

                        if aliasLocation is not None:
                            stringURL = stringURL + "  " + 'N{0}'.format(number_site(found_url))
                        else:
                            stringURL = stringURL + "     " + found_url

                if writepath is None:
                    logger.critical(stringURL)

                else:
                    logger.critical(stringURL)
                    file.write_on_file(stringURL)
                    file.write_on_file('\r\n')
                    file.write_on_file('\r\n')

            except IndexError:
                break

        current_depth += 1

        if not len(jobs[current_depth]):
            break

    logger.info('MISSION ACCOMPLISHED')
