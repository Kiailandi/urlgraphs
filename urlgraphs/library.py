from urlgraphs import logger


class Library(object):
    def __init__(self):
        self.urlDefRegistry = []

    def register(self, parser):
        logger.info('Register Parser: %s', parser)
        self.urlDefRegistry.append(parser)

    # found site's parser
    def get_parser_for(self, url):
        for urlParser in self.urlDefRegistry:
            if urlParser.match(url):
                return urlParser
