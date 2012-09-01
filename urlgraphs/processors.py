from collections import defaultdict, deque

from urlgraphs import logger


class Processor(object):
#    links search engine
    depth_root = 1
    current_depth = 1
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
        from urlgraphs.library import Library
        from urlgraphs import parsers

        self.site = Library()
        self.jobs = defaultdict(deque)
        self.linklist = []

        timeout = int(timeout)

        # parser define
        if __VBulletin_Section:
            self.site.register(parsers.VBulletin_Section(timeout))
        if __VBulletin_Topic:
            self.site.register(parsers.VBulletin_Topic(timeout))
        if __YahooAnswer:
            self.site.register(parsers.YahooAnswer(timeout))
        if __TuristiPerCaso:
            self.site.register(parsers.TuristiPerCaso(timeout))
        if __GenericLink:
            self.site.register(parsers.DiffbotParser(timeout))
        if __AlLink:
            self.site.register(parsers.EveryLinkParser(timeout))

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
        from urlparse import urlparse

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
        from urlparse import urlparse
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
        - find parser
        - find url and append in a list
        - yield tupla : (base url, [list of url])
        - increment current depth
        - fake tupla -> finish
        """
        logger.info('URL-Graphs --- START --- v3.1.0')
        self.current_depth = 1
        while True:
            while True:
                try:
                    url = self.jobs[self.current_depth].popleft()
                    self.current_job_index += 1

#                    if self.current_job_index > 200:
#                        exit()
                    parser = self.site.get_parser_for(url)
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
