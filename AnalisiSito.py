import requests
import re
from xml.etree import cElementTree as etree
from optparse import OptionParser

class File(object):

    def loadFile(self):
        file = open(readpath, 'r')
        s = file.readlines()
        file.close()
        return s

    def WriteOnFile(self,string):
        file = open(writepath, 'a')
        file.writelines(string)
        file.close()

    def WriteAlias(self):
        file = open(aliasLocation, 'a')
        for i in range(len(siteslist)):
            file.writelines('N' + str(i) + ': '+ siteslist[i])
            #print 'N' + i + ': '+ siteslist[i]
        file.close()

class DefSites(object):
    urlDefRegistry = []

    def register(self, parser):
        self.urlDefRegistry.append(parser)

    def get_parser_for(self, url):
        for urlParser in self.urlDefRegistry:
            if urlParser.regex.match(url):
                return urlParser

# ----------SITE CLASS -------------

class TuristiPerCaso(object):
    regex = re.compile('https?://www.turistipercaso.it')
    def run(self, url):
        pass


# SecondClass

class GenericLink(object):
    regex = re.compile('.*')

    def run(self, URL):
        self.URL = URL
        xmlanswer = requests.get(defpath, params=dict(token=s_token, url=URL)).text
        doc = etree.fromstring(xmlanswer.encode('utf-8'))
        for link in doc.iterfind('.//link'):
            yield link.text.strip()

# ----------------------------------

def parser():

    # python tsm.py --depth=3 --output=output.txt input.txt

    parser_ = OptionParser()
    parser_.add_option("-d", "--depth", dest="depth",
                      help="Level of depth on the net", metavar="number")
    parser_.add_option("-o", "--output", dest="output",
                      help="Location of file where save the data", metavar="data-location")
    parser_.add_option("-a", "--alias", dest="alias",
                      help="Location of file where save the alias-data", metavar="alias-location")

    (options, args) = parser_.parse_args()

    if options.depth is None or options.depth <= 0:
        depthRoot = 1
    else:
        depthRoot = int(options.depth)
    writepath = options.output
    aliasLocation = options.alias
    readpath = args[0]

    return depthRoot, writepath, readpath, aliasLocation

def doubleSite(URL):
    for i in range(len(siteslist)):
        if siteslist[i] == URL:
            return False
    return True

def numberSite(URL):

    try:
        return siteslist.index(URL)
    except ValueError:
        siteslist.append(URL)
        return len(siteslist)-1

# DELETE
# ----- inizialization -----

defpath = 'http://www.diffbot.com/api/frontpage'

s_token = '22df3421e2ecce206e95c4e68b44b9aa'

# ------------------------
# DELETE


# ----------MAIN -------------

if __name__ == "__main__":

    print '\r\n'
    print 'Avvio programma Analisi v0.1'
    print '\r\n'

    defSite = DefSites()
    defSite.register(TuristiPerCaso())
    defSite.register(GenericLink())

    depthRoot, writepath, readpath, aliasLocation = parser()

    siteslist = []
    file = File()
    job = file.loadFile()

    #  DuplaInizialization
    for i in range(len(job)):
        job[i] = job[i].strip(), 1

    for dsite in job:
        print dsite

    while True:
        if not len(job):
            break

        url, siteDepth = job.pop()
        parser = defSite.get_parser_for(url)
        print '\r\n'
        print 'Analisi sito: ' + url
        print 'Profondita\': ' + str(siteDepth)

        if writepath is not None:
            stringURL = 'N{0}'.format(numberSite(url))
        else:
            stringURL = url

        for found_url in parser.run(url):
            if writepath is not None:
                stringURL = stringURL + "     " + numberSite(found_url)
            else
                stringURL = stringURL + found_url
            siteslist.append(found_url)
            if siteDepth < depthRoot and doubleSite(found_url) :
                job.append((found_url, siteDepth + 1))

        if writepath is None:
            print stringURL
            print '\r\n'
            print '\r\n'
        else:
            file.WriteOnFile(stringURL)
            file.WriteOnFile('\r\n')
            file.WriteOnFile('\r\n')

    if aliasLocation is not None:
        print 'Scrittura alias'
        file.WriteAlias()

    print 'Operazione Terminata'
