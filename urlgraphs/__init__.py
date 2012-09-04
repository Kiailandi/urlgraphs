import os
import logging
from optparse import OptionParser
#import pdb


# logging level initialization
logger = logging.getLogger('debug_application')
logger.setLevel(logging.DEBUG)

# file handler
fdh = logging.FileHandler('debug.log')
fdh.setLevel(logging.ERROR)
file_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fdh.setFormatter(file_log_formatter)
logger.addHandler(fdh)

# console handler
cwh = logging.StreamHandler()
cwh.setLevel(logging.CRITICAL)
console_warnig_formatter = logging.Formatter('%(message)s')
cwh.setFormatter(console_warnig_formatter)
logger.addHandler(cwh)


# cache path
PROJECT_PATH = os.path.dirname(__file__)
CACHE_PATH = os.environ.get(
    'CACHE_PATH',
    os.path.join(os.path.dirname(__file__), '.cache')
)
#THREADED = False
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


class Tsm(object):
    def __init__(self):
        from collections import defaultdict

        self.edges = defaultdict(list)

    def parse_options(self):
        """
        Parse params
        python Tsm.py --depth=3 --output=output.txt input.txt
        """

        usage = "usage: %prog [options] inputfile"
        parser_ = OptionParser(usage=usage)
        parser_.add_option(
            "-d", "--depth", dest="depth",
            help="Level of depth on the net", metavar="number"
        )
        parser_.add_option(
            "-o", "--output", dest="output",
            help="Location of file where save the data",
            metavar="data-location"
        )
        parser_.add_option(
            "-a", "--alias", dest="alias",
            help="Location of file where save the alias-data",
            metavar="alias-location"
        )
        parser_.add_option(
            "--hostnames", dest="use_hostnames",
            help="Create a hostname network instead of a URL network",
            action="store_true",
            default=False,
        )
        parser_.add_option(
            '--format', dest="format", default="graphml",
            help="Specify an output format. Choose between dl and graphml. "
                "Default: graphml",
            action="store",
        )

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

        if options.format not in ('graphml', 'dl'):
            raise TypeError('Unknown format')

        self.output_path = options.output
        self.alias_path = options.alias
        self.input_path = args[0]
        self.use_hostnames = options.use_hostnames
        self.max_depth = depth_root
        self.format = options.format

    def run(self):
        from urlgraphs.processors import Processor

        self.parse_options()
        self.file = File(self.input_path, self.output_path, self.alias_path)

        for path in (self.output_path, self.alias_path):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass

        temp = self.file.load_file()
        self.process = Processor(
            temp,
            self.max_depth,
            True,
            True,
            True,
            True,
            True,
            False,
            30
        )

        for source, dests in self.process.analysis():
            self.elaborate_edges(source, dests)

        self.close()

    def elaborate_edges(self, source, dests):
        self.edges[source] = dests

    def write_dl(self, index):
        if self.alias_path:
            for i, site in enumerate(index):
                self.file.write_alias(i, site)

        for source, dests in self.edges.iteritems():
            self.file.write_on_file(
                'N{0}  '.format(index.index(source))
            )
            self.file.write_on_file(
                '  '.join([
                'N{0}'.format(index.index(dest))
                for dest in dests
                ])
            )
            self.file.write_on_file('\r\n')
            self.file.write_on_file('\r\n')

    def write_graphml(self, index):
        import igraph as ig
        from collections import Counter

        graph = ig.Graph(n=len(index), directed=True)
        graph.vs['url'] = index

        for source, dests in self.edges.iteritems():
            source_idx = index.index(source)
            grouped_dests = Counter(dests)
            for dest, weight in grouped_dests.iteritems():
                dest_idx = index.index(dest)

                graph.add_edge(source_idx, dest_idx)
                eid = graph.get_eid(source_idx, dest_idx, directed=True)
                graph.es[eid]['weight'] = weight

#        with open(, 'wb') as f:
        graph.write_graphmlz('output.graphmlz')

    def close(self):
        from collections import defaultdict

        def hostname(url):
            from urlparse import urlparse

            return urlparse(url).hostname

        if self.use_hostnames:
            hostname_edges = defaultdict(list)

            for source, dests in self.edges.iteritems():
                hostname_edges[hostname(source)] += map(hostname, dests)

            # sort and create the new index
            hostnames = set()
            for source in hostname_edges.iterkeys():
                new_edges = sorted(hostname_edges[source])
                hostname_edges[source] = new_edges
                hostnames.update(new_edges + [source])

            self.edges = hostname_edges
            index = list(hostnames)
        else:
            index = self.process.linklist

        if self.format == 'dl':
            self.write_dl(index)
        elif self.format == 'graphml':
            self.write_graphml(index)


if __name__ == "__main__":
    tsm = Tsm()
    tsm.run()
