import unittest

class TestMyModule(unittest.TestCase):

#    def test_sitesRegisterInizializzation(self):
#        from AnalisiSito import DefSites
#        import re
#        a = DefSites()
#        regex = re.compile('www.google.it')
#        a.register(regex)
#        self.assertListEqual(a.urlDefRegistry,[regex])
#        a.register('www.tuttogratis.com')
#        self.assertListEqual(a.urlDefRegistry,['www.google.it','www.tuttogratis.com'])

#    def test_get_parser_for(self):
#        from AnalisiSito import DefSites
#
#        a = DefSites()
#        a.register('www.google.it')
#        self.assertEqual(a.get_parser_for('www.google.it'), 'www.google.it')

   def test_Parser(self):
       from site_analysis import Parser
       import re

       parser = Parser()
       self.assertFalse(parser.match('www.google.it'))

       parser.regex = re.compile('www.google.it')
       self.assertTrue(parser.match('www.google.it'))


   def test_clear_site(self):
        from site_analysis import clear_site

        self.assertEqual(clear_site('http://www.miosito.com:80/pagina.html'),'http://www.miosito.com/pagina.html')
        self.assertEqual(clear_site('http://www.miosito.com:80/pagina.html?params=params'), 'http://www.miosito.com/pagina.html?params=params')


   def  test_Generic_link(self):
       from site_analysis import Generic_link
       gl = Generic_link()
       l = []
       for found_url in gl.run('http://www.diffbot.com/'):
           l.append(found_url)
       self.assertListEqual(l,['http://www.diffbot.com:80/our-apis'])


   def test_gen_hash(self):
       from site_analysis import gen_hash
       #self.assertEqual(gen_hash('http://www.diffbot.com/',dict(p1='p1', p2='p2')),'1905959970210950507')
       self.assertEqual(gen_hash('http://www.diffbot.com/',dict(p1='p1', p2='p2')),'1534481045')

   def test_is_valid(self):
       from site_analysis import is_valid
       self.assertTrue(is_valid('http://wwww.miosito.com/path.html'))
       self.assertFalse(is_valid('http://wwww.miosito.com/path.html?idfoto=0001'))
       self.assertFalse(is_valid('http://wwww.miosito.com/immagini/path.html'))

   def test_VBulletin_Topic(self):
       from site_analysis import VBulletin_Topic
       from bs4 import BeautifulSoup
       import requests
       vbt = VBulletin_Topic()
       self.assertTrue(vbt.match('http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html'))
       self.assertFalse(vbt.match('http://www.google.it'))
       text_soup = BeautifulSoup(requests.get('http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html').text, "lxml")
       self.assertEqual(len(list(vbt.found_pages(text_soup))),9)
       self.assertEqual(len(list(vbt.messages_url(text_soup))),9)
       self.assertEqual(len(list(vbt.run('http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html'))),18)

   def test_VBUlletin_Section(self):
       from site_analysis import VBulletin_Section
       vbt = VBulletin_Section()
       self.assertTrue(vbt.match('http://www.ilgiramondo.net/forum/trentino-alto-adige/'))
       self.assertFalse(vbt.match('http://www.google.it'))
       self.assertEqual(len(list(vbt.run('http://www.ilgiramondo.net/forum/trentino-alto-adige/'))),131)


#   def test_number_Site(self):
#        from analisi_sito import number_site, siteslist
#        self.assertTrue(number_site('www.mioURL.it') == len(siteslist)-1)




if __name__ == "__main__":
    unittest.main()
