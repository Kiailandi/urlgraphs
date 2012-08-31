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
        from urlgraphs.processors import Processor

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
