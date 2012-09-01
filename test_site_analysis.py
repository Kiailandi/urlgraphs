import re
import unittest
from site_analysis import GenericLink
from site_analysis import VBulletin_Topic
from site_analysis import VBulletin_Section
from site_analysis import TuristiPerCaso
from site_analysis import YahooAnswer
from site_analysis import AlLink
from site_analysis import Processor

from bs4 import BeautifulSoup
import requests

class TestIsValid(unittest.TestCase):
    process = Processor([], 1)

    def test_univoce_url_valid(self):
        self.assertTrue(
            self.process.is_valid('http://it.wikipedia.org/wiki/Python/'))

    def test_pdf_is_not_valid(self):
        self.assertFalse(self.process.is_valid('http://fakeurl.it/doc.pdf'))

    def test_javascript_protocol_not_allowed(self):
        self.assertFalse(self.process.is_valid('javascript://'))

    def test_showthread_attachement_validation(self):
        self.assertFalse(self.process.is_valid(
            'http://www.fassaforum.com/attachment.php?s=0f2a782eb8404a03f30d91df3d7f7ca5&attachmentid=702&d=1280593484'))
        self.assertFalse(self.process.is_valid(
            'http://showthread.php/?s=8714a40618cf41351b24bd0cbd6729d7&p=884417#post884417'))

    def test_is_member_validation(self):
        self.assertFalse(self.process.is_valid(
            'http://www.forumviaggiatori.com/members/norman+wells.htm'))

    def test_mailto_is_not_valid(self):
        self.assertFalse(self.process.is_valid('mailto:mail_user@webhost.com'))

    def test_TuristiPerCaso_abuse_is_not_valid(self):
        self.assertFalse(self.process.is_valid(
            'http://turistipercaso.it/forum/p/abuse/775751/'))

    def test_TuristiPerCaso_abuse_is_not_valid(self):
        self.assertFalse(
            self.process.is_valid('http://turistipercaso.it/u/u/login/?popup'))

    def test_photo_are_not_allowed(self):
        self.assertFalse(self.process.is_valid(
            'http://www.ilturista.info/ugc/foto_viaggi_vacanze/'
            '455-Le_cascate_piu_belle_grandi_o_spettacolari_del_mondo/?idfoto=8704'))
        self.assertFalse(self.process.is_valid(
            'http://www.ilturista.info/ugc/immagini/giordania/asia/1822/'))
        self.assertFalse(
            self.process.is_valid('http://www.ilturista.info/photogallery/'))

    def test_photo_fake_url_not_allowed(self):
        self.assertFalse(self.process.is_valid('http://fakeurl.it/'))

    def test_too_many_redirections(self):
        self.assertFalse(self.process.is_valid(
            'http://download.repubblica.it/ultimominuto/info_page.jsp'))


class Parser(unittest.TestCase):
    def test_Parser_not_valid(self):
        from site_analysis import Parser

        parser = Parser()
        self.assertFalse(parser.match('www.google.it'))

    def test_Parser_valid(self):
        from site_analysis import Parser

        parser = Parser()
        parser.regex = re.compile('www.google.it')
        self.assertTrue(parser.match('www.google.it'))


class TestClearSite(unittest.TestCase):
    process = Processor([], 1)

    def test_clear_port_80(self):
        self.assertEqual(
            self.process.clear_site('http://www.miosito.com:80/pagina.html/'),
            'http://www.miosito.com/pagina.html/')

    def test_clear_space(self):
        self.assertEqual(self.process.clear_site(
            'http://www.viagginrete-it.it/vacanze/vacanze per famiglie/'),
                         'http://www.viagginrete-it.it/vacanze/vacanze%20per%20famiglie/')

    def test_clear_port_80(self):
        self.assertEqual(self.process.clear_site(
            'http://www.miosito.com:80/pagina.html?params=params'),
                         'http://www.miosito.com/pagina.html?params=params')

    def test_clear_print(self):
        self.assertEqual(
            self.process.clear_site('http://www.miosito.com/pagina.html/print')
            , 'http://www.miosito.com/pagina.html/')
        self.assertEqual(self.process.clear_site(
            'http://www.miosito.com/pagina.html/print/'),
                         'http://www.miosito.com/pagina.html/')


class TestGenericLink(unittest.TestCase):
    def test_diffbot_api(self):
        gl = GenericLink()
        l = []
        for found_url in gl.run('http://www.diffbot.com/'):
            l.append(found_url)

        self.assertIn('http://www.diffbot.com:80/our-apis', l)


class TestGeHash(unittest.TestCase):
    def test_hash_equals(self):
        from site_analysis import gen_hash
        #self.assertEqual(gen_hash('http://www.diffbot.com/',dict(p1='p1', p2='p2')),'1905959970210950507')
        # insert new hash
        self.assertEqual(
            gen_hash('http://www.diffbot.com/', dict(p1='p1', p2='p2')),
            gen_hash('http://www.diffbot.com/', dict(p1='p1', p2='p2')))


class TestVBulletinTopic(unittest.TestCase):
    vbt = VBulletin_Topic()

    def test_VBulletin_Topic_match(self):
        self.assertTrue(self.vbt.match(
            'http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html'))

    def test_VBulletin_Topic_false(self):
        self.assertFalse(self.vbt.match('http://www.google.it'))

    def test_VBulletin_Topic_run_on_page(self):
        text_soup = BeautifulSoup(requests.get(
            'http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html').text
                                  , "lxml")
        self.assertEqual(len(list(self.vbt.find_pages(text_soup))), 9)
        self.assertEqual(len(list(self.vbt.messages_url(text_soup))), 9)
        self.assertEqual(len(list(self.vbt.run(
            'http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html')))
                         , 18)


class TestVBulletinSection(unittest.TestCase):
    vbt = VBulletin_Section()

    def test_VBulletin_Section_match(self):
        self.assertTrue(self.vbt.match(
            'http://www.ilgiramondo.net/forum/trentino-alto-adige/'))

    def test_VBulletin_Section_false(self):
        self.assertFalse(self.vbt.match('http://www.google.it'))

    def test_VBulletin_Section_run_on_page(self):
        self.assertEqual(len(list(self.vbt.run(
            'http://www.ilgiramondo.net/forum/trentino-alto-adige/'))), 132)


class TestTuristiPerCaso(unittest.TestCase):
    tpc = TuristiPerCaso()

    def test_TuristiPerCaso_match(self):
        self.assertTrue(self.tpc.match(
            'http://turistipercaso.it/forum/t/71583/isole-della-grecia.html'))
        self.assertTrue(self.tpc.match(
            'https://turistipercaso.it/forum/t/71583/isole-della-grecia.html'))
        self.assertTrue(self.tpc.match(
            'http://www.turistipercaso.it/forum/t/71583/isole-della-grecia.html'))
        self.assertTrue(self.tpc.match(
            'https://www.turistipercaso.it/forum/t/71583/isole-della-grecia.html'))

    def test_TuristiPerCaso_run_on_page(self):
        grecia_soup = BeautifulSoup(requests.get(
            'http://turistipercaso.it/forum/t/71583/isole-della-grecia.html').text
                                    , "lxml")
        self.assertEqual(len(list(self.tpc.find_paginator(grecia_soup))), 6)
        messico_soup = BeautifulSoup(requests.get(
            'http://turistipercaso.it/forum/t/194776/holbox-messico.html').text
                                     , "lxml")
        self.assertEqual(len(list(self.tpc.find_paginator(messico_soup))), 0)
        self.assertEqual(len(list(self.tpc.run(
            'http://turistipercaso.it/forum/t/71583/isole-della-grecia.html')))
                         , len(list(self.tpc.run(
                'http://turistipercaso.it/forum/t/71583/isole-della-grecia.html'))))


class TestYahooAnswer(unittest.TestCase):
    ya = YahooAnswer()

    def test_Yahoo_Answer_match(self):
        self.assertTrue(self.ya.match(
            'http://it.answers.yahoo.com/question/index?qid=20120617101809AAaPAeO')) #Topic
        self.assertTrue(self.ya.match(
            'http://it.answers.yahoo.com/dir/index;_ylt=AlfwvVcRJfbSNGQd1gwtODlGWH1G;_ylv=3?sid=396546975&link=resolved#yan-questions')) #Section
        self.assertFalse(self.ya.match('https://login.yahoo.com/'))

    def test_Yahoo_Answer_run_on_page(self):
        self.assertEqual(len(list(self.ya.run(
            'http://it.answers.yahoo.com/question/index?qid=20120617101809AAaPAeO')))
                         , 1)
        self.assertEqual(len(list(self.ya.run(
            'http://it.answers.yahoo.com/dir/index;_ylt=AlfwvVcRJfbSNGQd1gwtODlGWH1G;_ylv=3?sid=396546975&link=resolved#yan-questions')))
                         , 20)

    def test_Yahoo_Answer_parser_threads(self):
        self.assertIsNone(self.ya.yahoo_page_parser(
            'http://it.answers.yahoo.com/question/index?qid=20120617101809AAaPAeO')[
                          0])
        thread_topics, messages_topic = self.ya.yahoo_page_parser(
            'http://it.answers.yahoo.com/dir/index;_ylt=AlfwvVcRJfbSNGQd1gwtODlGWH1G;_ylv=3?sid=396546975&link=resolved#yan-questions')
        self.assertEqual(len(list(self.ya.found_thread_topics(thread_topics))),
                         20)

    def test_Yahoo_Answer_parser_topic_messages(self):
        thread_topics, messages_topic = self.ya.yahoo_page_parser(
            'http://it.answers.yahoo.com/question/index?qid=20120617101809AAaPAeO')
        self.assertEqual(
            len(list(self.ya.found_messages_topic(messages_topic))), 1)


class TestAlLink(unittest.TestCase):
    al = AlLink()

    def test_AlLink_run_on_page(self):
        self.assertEqual(
            len(list(self.al.run('http://www.mentalhealthforum.ch'))), 14)


class TestProcessor(unittest.TestCase):
    def setUp(self):
        self.process = Processor(
            ['http://forum.zingarate.com/campo-tures-59705.html'],
                                                                 3,
                                                                 False,
                                                                 True,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 False,
                                                                 30
        )

    def test_index_site(self):
        self.assertEqual(self.process.link_index('http://www.google.it/'), -1)
        self.assertEqual(
            self.process.link_index(
                'http://forum.zingarate.com/campo-tures-59705.html'
            ),
            0
        )

    def test_absolutize(self):
        self.assertEqual(
            self.process.absolutize(
                '/contatti', 'http://www.google.it'
            ),
            'http://www.google.it/contatti'
        )

#    def test_analysis(self):
#        self.assertEqual(len(list(self.process.analysis())), 2)
