import os
import logging
from collections import defaultdict, deque
from optparse import OptionParser
from urlparse import urlparse
#import pdb


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
CACHE_PATH = os.environ.get(
    'CACHE_PATH',
    os.path.join(os.path.dirname(__file__), '.cache')
)
THREADED = False
WORKERS = 2


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


class DefSites(object):
    # sites' rules

    def __init__(self):
        self.urlDefRegistry = []

    def register(self, parser):
        logger.info('Register Parser: %s', parser)
#        assert isinstance(parser, Parser), \
#            "Mi aspettavo un parser, mi hai passato un {0}".format(
#                type(parser)
#            )
        self.urlDefRegistry.append(parser)

    # found site's parser
    def get_parser_for(self, url):
        for urlParser in self.urlDefRegistry:
            if urlParser.match(url):
                return urlParser


#import threading
#
#class UrlGetWorker(threading.Thread):
#    def __init__(self, queue, name):
#        super(UrlGetWorker, self).__init__()
#
#        self.queue = queue
#        self.name = name
#
#    def run(self):
#        while True:
#            try:
#                url = self.queue.get(True, 10)
#            except:
#                logger.warning('Thread %s has nothing to do', self.name)
#                pass
#            else:
##                if url is None:
##                    return
#                logger.warning('Thread %s gets url %s', self.name, url)
#                get(url)
#                self.queue.task_done()


class Processor(object):
#    links search engine
    depth_root = 1
    current_depth = 1
    linklist = []
    def_site = DefSites()
    jobs = defaultdict(deque)
    current_job_index = 0

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
        from urlgraphs import parsers

        timeout = int(timeout)
        # parser define
        if __VBulletin_Section:
            self.def_site.register(parsers.VBulletin_Section(timeout))
        if __VBulletin_Topic:
            self.def_site.register(parsers.VBulletin_Topic(timeout))
        if __YahooAnswer:
            self.def_site.register(parsers.YahooAnswer(timeout))
        if __TuristiPerCaso:
            self.def_site.register(parsers.TuristiPerCaso(timeout))
        if __GenericLink:
            self.def_site.register(parsers.GenericLink(timeout))
        if __AlLink:
            self.def_site.register(parsers.AlLink(timeout))

#        if THREADED:
#            from Queue import Queue
#            self.url_queue = Queue()
#
#            # clean locks
#            from redis import Redis
#            red = Redis()
#            for k in red.keys('LOCK:*'):
#                logger.info('Remove key %s', k)
#                red.delete(k)
#
#            for i in range(WORKERS):
#                worker = UrlGetWorker(self.url_queue, i)
#                worker.setDaemon(True)
#                worker.start()

        self.depth_root = depth_root
        self.linklist_initialization(templist)

    def linklist_initialization(self, templist):
        for url in templist:
            url = url.strip()
            if not url:
                continue
            if self.is_valid(url):
                url = self.clear_site(url)

                self.linklist.append(url)
                self.analyze_this(url, 1)

    # ---------------------------------

    def analyze_this(self, url, depth):
        logger.warning('New link to analyze %s', url)
        self.jobs[depth].append(url)
#        if THREADED:
#            self.url_queue.put(url)

    def link_index(self, url):
        """
        return the index of the 'url' in the sites_list
        """
#        logger.info('Check number for url: %s', url)
        try:
            return self.linklist.index(url)
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
        from urlgraphs.helpers import get

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

        # http://www.forumviaggiatori.com/members/norman+wells.htm
        if url.find('/members/') != -1:
        #        user login page
            logger.warning(inv + 'user login page: %s', url)
            return False

        # http://s3.mediastreaming.it/mobile.php?port=9022
        if url.find('streaming') != -1:
            logger.warning(inv + 'it\'s a streaming: %s', url)
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

        return True

    def run(self, url, parser):
    #        found links on url, with parser: XYZ
        for found_url in parser.run(url):
            found_url = self.clear_site(found_url, url)
            if self.is_valid(found_url):
                logger.info('found_url: %s', found_url)
                if self.link_index(found_url) == -1:
                    self.linklist.append(found_url)
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
                    self.current_job_index += 1

                    if self.current_job_index > 200:
                        exit()
                    parser = self.def_site.get_parser_for(url)
                    logger.critical('Site under analysis: %s', url)
                    logger.critical(
                        'Depth: %d. Current job: %d',
                        self.current_depth,
                        self.current_job_index
                    )
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

        logger.info(
            'Params: depth= %s, output=%s, alias=%s, read=%s',
            options.depth, options.output, options.alias,
            args[0]
        )

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
        process = Processor(
            temp,
            depth_root,
            True,
            True,
            True,
            True,
            True,
            False,
            30
        )

        if alias_location is not None and write_path is not None:
            for i, site in enumerate(process.linklist):
                file.write_alias(i, site)

        for tupla_url in process.analysis():
            if alias_location is not None:
                stringURL = 'N{0}'.format(process.link_index(tupla_url[0]))
            else:
                stringURL = tupla_url[0]

            for found_url in tupla_url[1]:
                if alias_location is None:
                    stringURL += "     " + found_url
                else:
                    index = process.link_index(found_url)
                    stringURL += '  N{0}'.format(index)
                    file.write_alias(index, process.linklist[index])

#            logger.critical(stringURL)
            if write_path is not None:
                file.write_on_file(stringURL)
                file.write_on_file('\r\n')
                file.write_on_file('\r\n')


if __name__ == "__main__":
    tsm = Tsm()
    tsm.main_tsm()
