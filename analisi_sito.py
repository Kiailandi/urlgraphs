import requests
import re
import os
from xml.etree import cElementTree as etree
from collections import defaultdict
from optparse import OptionParser
from urlparse import urlparse
from bz2 import BZ2File

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
        file = open(readpath, 'r')
        s = file.readlines()
        file.close()
        return s

    def write_on_file(self,string):
        file = open(writepath, 'a')
        file.writelines(string)
        file.close()

    def write_alias(self):
        os.remove(aliasLocation)
        file = open(aliasLocation, 'a')
        for i in range(len(siteslist)):
            file.writelines('N' + str(i) + ': '+ siteslist[i] +'\r\n')
        file.close()

class DefSites(object):
    # sites' rules

    def __init__(self):
        self.urlDefRegistry = []

    def register(self, parser):
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

class VBullettin(Parser):

    """

----------------------------- Section ---------------------------------


    # http://www.ilgiramondo.net/forum/trentino-alto-adige/

     # URL Topic:
    <a class="title" href="http://www.ilgiramondo.net/forum/trentino-alto-adige/21531-trentino-alto-adige-renon.html" id="thread_title_21531">Trentino Alto Adige - Renon</a>

    # Paginetion Topic

    <dl class="pagination" id="pagination_threadbit_15753">
								<dt class="label">25 Pagine <span class="separator">&bull;</span></dt>
								<dd>
									<span class="pagelinks">
										 <span><a href="http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html">1</a></span> <span><a href="http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/15753-trentino-alto-adige.html">2</a></span> <span><a href="http://www.ilgiramondo.net/forum/page-3/trentino-alto-adige/15753-trentino-alto-adige.html">3</a></span>
										 ... <a href="http://www.ilgiramondo.net/forum/page-25/trentino-alto-adige/15753-trentino-alto-adige.html">25</a>
									</span>
								</dd>
							</dl>

----------------------------- Topic ---------------------------------

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

# Notice '><!-- google_ad_section_start -->'             '<!-- google_ad_section_end --><!-- GAL -->'

    """
    def match(self, url):
        text = get(url)

        # if text matches return True

        return False

    def run(self, url):
        print 'Applico i criteri di vBulletin'



        pass


class GenericLink(Parser):
    # diffbot's analysis
    def match(self, url):
        return True

    # list of link by diffbot
    def run(self, URL):
        self.URL = URL
        xmlanswer = get(defpath, params=dict(token=s_token, url=URL))
        doc = etree.fromstring(xmlanswer.encode('utf-8'))
        for link in doc.iterfind('.//link'):
            yield link.text.strip()

# ----------------------------------

def gen_hash(*args, **kwargs):
    # hash file generator (for caching)
    import cPickle as pickle
    return str(abs(hash(pickle.dumps((args, kwargs)))))

def get(url, **kwargs):
    # hash site

    hash_ = gen_hash(url, kwargs)
    filename = os.path.join(CACHE_PATH, hash_) + '.bz2'

    # search in cache
    try:
        with BZ2File(filename, 'rb') as f:
            return f.read().decode('utf-8')
    except IOError:
        pass

    text = requests.get(url, **kwargs).text

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
    try:
        return siteslist.index(url)
    except ValueError:
        siteslist.append(clear_site(url))
        return len(siteslist)-1

def clear_site(url):
    # formatting and clearing url
    s = urlparse(url)

    if s.query =='':
        site = s.scheme + '://' + s.hostname + s.path
    else:
        site = s.scheme + '://' + s.hostname + s.path + '?' + s.query

    return site

# DELETE
# ----- inizialization -----

defpath = 'http://www.diffbot.com/api/frontpage'

s_token = '22df3421e2ecce206e95c4e68b44b9aa'

# ------------------------
# DELETE


# ----------MAIN -------------

if __name__ == "__main__":

    print '\r'
    print 'Avvio programma Analisi v0.1'
    print '\r'

    # class define
    defSite = DefSites()
    defSite.register(VBullettin())
    defSite.register(TuristiPerCaso())
    defSite.register(GenericLink())

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

    #  dictionary's inizialization
    for i in range(len(temp)):
        siteslist.append(clear_site(temp[i].strip()))
        jobs[1].append(clear_site(temp[i].strip()))

    currentDepth = 1

    while True:
        while True:
            try:
                url = jobs[currentDepth].pop()
                parser = defSite.get_parser_for(url)
                print '\r'
                print 'Analisi sito: ' + url
                print 'Profondita\': ' + str(currentDepth)

                if writepath is not None:
                    stringURL = 'N{0}'.format(number_site(url))
                else:
                    stringURL = url

                for found_url in parser.run(url):

                    found_url = clear_site(found_url)

                    if number_site(found_url) == len(siteslist)-1 and currentDepth < depthRoot:
                        jobs[currentDepth+1].append(found_url)

                    if writepath is not None:
                        stringURL = stringURL + "  " + 'N{0}'.format(number_site(found_url))
                    else:
                        stringURL = stringURL + "     " + found_url

                if writepath is None:
                    print stringURL
                    print '\r'

                else:
                    file.write_on_file(stringURL)
                    file.write_on_file('\r\n')
                    file.write_on_file('\r\n')
            except IndexError:
                break

        currentDepth +=1

        if not len(jobs[currentDepth]):
            break

    if aliasLocation is not None:
        print 'Scrittura alias'
        file.write_alias()

    print 'Operazione Terminata'
