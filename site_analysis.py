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

# logging level initialization
logging.basicConfig(level=logging.DEBUG)

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
        logging.info('Open read file from path: %s', readpath)
        file = open(readpath, 'r')
        s = file.readlines()
        file.close()
        return s

    def write_on_file(self, string):
        logging.info('Write on file, path: %s', writepath)
        file = open(writepath, 'a')
        file.writelines(string)
        file.close()

    def write_alias(self):
        logging.info('Write alias file, path: %s', readpath)
        os.remove(aliasLocation)
        file = open(aliasLocation, 'a')
        for i in range(len(siteslist)):
            file.writelines('N' + str(i) + ': ' + siteslist[i].encode('utf-8') + '\r\n')
        file.close()


class DefSites(object):
    # sites' rules

    def __init__(self):
        self.urlDefRegistry = []

    def register(self, parser):
        logging.info('Register Parser: %s', parser)
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


class TuristiPerCaso(Parser):
    regex = re.compile('https?://www.turistipercaso.it')

    def run(self, url):
        pass


class VBulletin_Section(Parser):
    """

----------------------------- Section ---------------------------------

    # http://www.ilgiramondo.net/forum/trentino-alto-adige/

     # URL Topic:
    <a class="title" href="http://www.ilgiramondo.net/forum/trentino-alto-adige/21531-trentino-alto-adige-renon.html" id="thread_title_21531">Trentino Alto Adige - Renon</a>

    # Paginetion Topic
    <div id="threadlist" class="threadlist">
        < > ... < >
            <dl class="pagination" id="pagination_threadbit_15753">
                <dt class="label">25 Pagine <span class="separator">&bull;</span></dt>
                        <dd>
                            <span class="pagelinks">
                                 <span><a href="http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html">1</a></span> <span><a href="http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/15753-trentino-alto-adige.html">2</a></span> <span><a href="http://www.ilgiramondo.net/forum/page-3/trentino-alto-adige/15753-trentino-alto-adige.html">3</a></span>
                                      ... <a href="http://www.ilgiramondo.net/forum/page-25/trentino-alto-adige/15753-trentino-alto-adige.html">25</a>
                                </span>
                            </dd>
                     </dl>
        < > ... < >
    </div>
    """

    def match(self, url):
#   found if is a VBulletin section
        logging.info('Check VBulletin section rules of the site: %s', url)
        page = get(url)
        section_soup = BeautifulSoup(page, "lxml")
        html = section_soup.find('html')
        f_section = section_soup.find('div',{"id":"threadlist"},{"class":"threadlist"})
#        try: # is possible html.get('id') == None
        if html.get('id') == 'vbulletin_html' and f_section is not None:
            return True
#        except:
#                return False

        return False

    def found_topic_url(self, div):
#   found by how many topic is composed the forum section
        for topic in div.find_all('a', {"class": "title"}):
            yield topic.get('href')

    def found_pagination(self,div):
#   found if is use a pagination for the topic
        for page in div.find_all('span', {"class": "pagelinks"}): #<span class="pagelinks">
            for url_topic in page.find_all('a'):
                yield url_topic.get('href')

    def run(self,url):
        logging.info('Run VBulletin section rules of the site: %s', url)
        print 'Applico criteri vBulletin_Section'
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
    """ ----------------------------- Topic ---------------------------------
    <div id="postlist" class="postlist">

    Page 1: http://www.ilgiramondo.net/forum/trentino-alto-adige/6669-trentino-alto-adige-quale-localita.html
    Page 2: http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/6669-trentino-alto-adige-quale-localita.html

    URL in users' message
    <div class="content">
    <div id="post_message_340346">

    <!-- google_ad_section_start -->Io sono stata a Levico Terme a Natale .. c'erano i mercatini, ma mi sembrava carino anche per l'estate.<br />
Non so come sia per la vita serale.. pero' le terme sono carine, c'e' anche la piscina e la sauna nell'hotel.<br />
<a onclick="_gaq.push(['_trackEvent', 'Outgoing', 'www.eden-hotel.com', '']);" rel="nofollow" href="http://www.eden-hotel.com" target="_blank">www.eden-hotel.com</a><!-- google_ad_section_end --><!-- GAL -->
    </div>
</div>

# Notice: '><!-- google_ad_section_start -->'             '<!-- google_ad_section_end --><!-- GAL -->'
    """

    def match(self, url):
#   found if is a VBulletin topic
        logging.info('Check VBulletin topic rules of the site: %s', url)
        page = get(url)
        topic_soup = BeautifulSoup(page, "lxml")
        html = topic_soup.find('html')
        f_topic = topic_soup.find('div',{"id":"postlist"},{"class":"postlist restrain"})
#        try: # is possible html.get('id') == None
        if html.get('id') == 'vbulletin_html' and f_topic is not None:
            return True
#        except:
#            return False

        return False

    def found_pages(self, text_soup):
#   found by how many pages is composed the topic
#   <div id="pagination_top" class="pagination_top">
        div_lists = text_soup.find('div', {'id':'pagination_top'}, {'class':'pagination_top'})
        for a in div_lists.find_all('a'):
            if a.get('href'):
                yield a.get('href')

    def messages_url(self,text_soup):
#   found URL in users' messages
        div_lists = text_soup.find_all('div', {"class": "content"}) # type list
        for div in div_lists:
            for a in div.find_all('a'):
                if a.get('href'):
                    yield a.get('href')

    def run(self,url):
        logging.info('Run VBulletin section rules of the site: %s', url)
        print 'Applico criteri di vBulletin_Topic'
        page = get(url)
        text_soup = BeautifulSoup(page, "lxml")
        for page_link in self.messages_url(text_soup):
            yield page_link
        for pages in self.found_pages(text_soup):
            yield pages


class Generic_link(Parser):
# diffbot's analysis
    def match(self, url):
        return True

    # list of link by diffbot
    def run(self, url):
        logging.info('Run Diffbot on site: %s', url)
        print 'Applico criteri Diffbot'
        try:
            xmlanswer = get(defpath,60, params=dict(token=s_token, url=url))
        except requests.exceptions.Timeout:
            print 'Diffbot sta impiegando troppo tempo per la risposta, salto il link'
            return
        try:
            doc = etree.fromstring(xmlanswer.encode('utf-8'))
        except:
            return
        for link in doc.iterfind('.//link'):
            yield link.text.strip()


# ----------------------------------

def gen_hash(*args, **kwargs):
# hash file generator (for caching)

    import cPickle as pickle
    return str(abs(hash(pickle.dumps((args, kwargs)))))

def get(url, timeout=30, **kwargs):
    logging.info('Getting url %s', url)
    # hash request
    hash_ = gen_hash(url, kwargs)
    filename = os.path.join(CACHE_PATH, hash_) + '.bz2'

    # search in cache
    try:
        with BZ2File(filename, 'rb') as f:
            logging.info('Found in cache: %s', url)
            return f.read().decode('utf-8')
    except IOError:
        pass

    print url
    logging.info('Not in cache: %s', url)
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
    logging.info('Params: depth= %d, output=%s, alias=%s, read=%s', options.depth, options.output, options.alias, args[0])

    # check option (depth)
    if options.depth is None or options.depth <= 0:
        depthRoot = 1
    else:
        depthRoot = int(options.depth)
    #

    writepath = options.output
    aliasLocation = options.alias
    readpath = args[0]

    return depthRoot, writepath, readpath, aliasLocation

def number_site(url):
    """
    return the index of the 'url' in the sites_list
    if doesn't exists add him
    """
    logging.info('Check number for url: %s',url)
    try:
        return siteslist.index(url)
    except ValueError:
        siteslist.append(clear_site(url))
        return len(siteslist) - 1

def clear_site(url):
    # formatting and clearing url
    s = urlparse(url)

#    print url, s.scheme, s.hostname, s.path
    logging.info('urlparse: %s',s)
    if s.query == '':
        try:
            site = s.scheme + '://' + s.hostname + s.path
        except TypeError:
            site = 'http://'+ s.path
    else:
        try:
            site = s.scheme + '://' + s.hostname + s.path + '?' + s.query
        except TypeError:
            site = 'http://'+ s.path + '?' + s.query

    return site


def is_valid(url):
    """
    function for found if an url is valid for the research

    showthread.php      showthread.php
    javascript://       javascript://
    www.google.it       scheme:""   path:"www.google.it"
    idfoto:             http://www.ilturista.info/ugc/foto_viaggi_vacanze/228-Foto_dell_Oktoberfest_tra_ragazze_e_boccali_della_festa_della_birra_di_Monaco/?idfoto=5161
    immagini:           http://www.ilturista.info/ugc/immagini/istanbul/turchia/6111/

    """
    logging.info('Url validation: %s', url)

    if url == 'javascript://':
        return False

    if url.find('showthread.php') > 0:
        return False

    s = urlparse(url)
    s_path = s.path.lower()
    s_query = s.query.lower()

    # try (don't sure if this section is utilizable)
#    try:
    if s.scheme.find('mailto') != -1:
        return False
#    except: AttributeError
#        pass

    if s.hostname is None and s.path is None:
        return False

    if s_path.find('immagini') != -1:
        ###### Image YES ########################
        imagepath = '\\home\\elia\\temp\\image.txt'
        logging.info('Write on file, path: %s', imagepath)
        file = open(imagepath, 'a')
        file.writelines(url + '\r\n')
        file.close()
        ######################################
        return False
    if s_query.find('idfoto') != -1:
        return False

    try:
        get(url)
    except:
        return False

#    except requests.exceptions.ConnectionError:
#        print 'Server non raggiungibile o inesistente'
#        logging.info('Server unreachable or nonexistent: %s', url)
#        return False
#
#    except requests.exceptions.Timeout:
#        print 'Il server sta impiegando troppo tempo per la risposta, salto il link'
#        logging.info('Timeout link: %s', url)
#        return False
#
#    except UnicodeError:
#        Fake link, or invalid extensions
#        print 'Url non valido'
#        logging.info('Url unacceptable: %s', url)
#        return False
#
#    except TypeError:
#        Invalid extensions
#        print 'Url non valido'
#        logging.info('Url unacceptable: %s', url)
#        return False

    return True

# DELETE
# ----- inizialization -----

defpath = 'http://www.diffbot.com/api/frontpage'

s_token = '22df3421e2ecce206e95c4e68b44b9aa'

# ------------------------
# DELETE


# ----------MAIN -------------

if __name__ == "__main__":
    print '\r'
    print 'Avvio programma Analisi v0.1.1'
    print '\r'

    # class define
    defSite = DefSites()
    defSite.register(VBulletin_Section())
    defSite.register(VBulletin_Topic())
#    defSite.register(TuristiPerCaso())
    defSite.register(Generic_link())

    depthRoot, writepath, readpath, aliasLocation = option_parser()
    siteslist = []
    file = File()
    if writepath is not None:
        try:
            os.remove(writepath)
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

    current_depth = 1

    while True:
        while True:
            try:
                url = jobs[current_depth].pop()
                parser = defSite.get_parser_for(url)
                print '\r'
                print 'Analisi sito: ' + url
                print 'Profondita\': ' + str(current_depth)

#                if is_valid(url) == False:
#                    break

                if writepath is not None:
                    if aliasLocation is not None:
                        stringURL = 'N{0}'.format(number_site(url))
                    else:
                         stringURL = url
                else:
                    print '\r'
                    stringURL = url + '\r\n'

                for found_url in parser.run(url):
                    if is_valid(found_url):
                        logging.info('found_url: %s',found_url)
                        found_url = clear_site(found_url)
                        if number_site(found_url) == len(siteslist) - 1 and current_depth < depthRoot:
                            jobs[current_depth + 1].append(found_url)

                        if writepath is not None:
                            if aliasLocation is not None:
                                stringURL = stringURL + "  " + 'N{0}'.format(number_site(found_url))
                            else:
                                stringURL = stringURL + "     " + found_url
                        else:
                            stringURL = stringURL + "     " + found_url + '\r\n'

                if writepath is None:
                    print stringURL

                else:
                    file.write_on_file(stringURL)
                    file.write_on_file('\r\n')
                    file.write_on_file('\r\n')
            except IndexError:
                break

        current_depth += 1

        if not len(jobs[current_depth]):
            break

    if aliasLocation is not None and writepath is not None:
        print 'Scrittura alias'
        file.write_alias()

    print 'Operazione Terminata'
