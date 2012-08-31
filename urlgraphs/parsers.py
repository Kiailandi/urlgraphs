import re
from itertools import chain

import requests
from lxml import etree

from urlgraphs import logger
from urlgraphs.helpers import get_soup_from_url, get


class Parser(object):
    regex = None
    timeout = 30

    def __init__(self, timeout=30):
        self.timeout = timeout

    def match(self, url):
        if self.regex:
            return self.regex.match(url)
        return False


class YahooAnswer(Parser):
    def yahoo_page_parser(self, url):
        page_soup = get_soup_from_url(url)
        # section
        thread_topics = page_soup.find('ul', {"class": "questions"})
        # topic and section
        messages_topic = page_soup.find('div', {"id": "yan-content"})
        return thread_topics, messages_topic

    def match(self, url):
    #   found if the url contains the acronym 'yahoo'
        logger.info('Check if is a Yahoo page: %s', url)
        if url.find('.yahoo.com') != -1:
            thread_topics, message_topic = self.yahoo_page_parser(url)
            if thread_topics is not None or message_topic is not None:
                return  True

        return False

    def found_thread_topics(self, section_topics):
    #        found thread questions in section
        h3_list = section_topics.findAll('h3')
        for h3 in h3_list:
            yield 'http://it.answers.yahoo.com/' + h3.find('a').get('href')

    def found_messages_topic(self, topic_messages):
    #        found messages in the topic question
        a_list = topic_messages.findAll('a', {'rel': 'nofollow'})
        for a in a_list:
            yield a.get('href')

    def run(self, url):
    #        start Yahoo answer rule
        thread_topics, messages_topic = self.yahoo_page_parser(url)
        if thread_topics is not None:
            for a in self.found_thread_topics(thread_topics):
                yield a
        else:
            for a in self.found_messages_topic(messages_topic):
                yield a


class TuristiPerCaso(Parser):
#    regex rule
    regex = re.compile(r'(https?://(www.)?)?turistipercaso.it/forum/')
    html_parser = None

    def __init__(self, timeout=30):
        import HTMLParser

        self.html_parser = HTMLParser.HTMLParser()
        super(TuristiPerCaso, self).__init__(timeout)

    @staticmethod
    def a_valid(a):
    #        rules for valid a_href URL
        try:
            href = a['href']
        except KeyError:
            return False

        # remove title
        if a.find_parent('h2'):
            return False

        #login pop
        if '?popup' in href:
            return False

        # flag
        if '/forum/p/abuse/' in href:
            return False

        # reply
        if '/forum/p/edit/' in href:
            return False

        cls = a.get('class')
        if cls and 'reply' in cls:
            return False

        #        mailto
        if href.startswith('mailto:'):
            return False

        return True

    def unescape_and_iter(self, text):
    #        unescape old links
        html = self.html_parser.unescape(text)
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all('a'):
            if self.a_valid(a):
                yield a['href']

    def found_paginator(self, text_soup):
    #        found URL pagination
    #        <div class="paginator" ... >
        page_div = text_soup.find('div', {'class': 'paginator'})
        if page_div is not None:
            ol = page_div.find('ol', {'class': 'center'})
            for url_topic in ol.find_all('a'):
                yield 'http://turistipercaso.it' + url_topic.get('href')

    def run(self, url, with_user=False):
    #        run TuristiPerCaso rules
        logger.info('Run TuristiPerCaso rules of the site: %s', url)
        text_soup = get_soup_from_url(url)
        f_section = text_soup.find('ol', {"class": "thread"})
        if f_section is not None:
            a_list = chain.from_iterable(
                forum_text.find_all('a') for forum_text in
                    f_section.find_all('div', {'class': 'forum_text'})
            )
            if with_user:
                a_list = chain(a_list, f_section.find_all('a', {'class': 'avatar'}))

            for a in a_list:
                if self.a_valid(a):
                    yield a['href']

                    #&lt;a href=&quot;http://viaggiareconibambini.blogspot.com/search/label/Alto%20Adige&quot;
                    #            encoding errors
            for forum_text in f_section.find_all('div', {'class': 'forum_text'}):
                # find escaped links in text
                text = forum_text.text
                for found_url in self.unescape_and_iter(text):
                    yield found_url

                # and in childs
                for tag in forum_text.find_all():
                    text = tag.text
                    for found_url in self.unescape_and_iter(text):
                        yield found_url
                        #            run paginator

            for a_page in self.found_paginator(text_soup):
                yield a_page
        else:
            return


class VBulletin_Section(Parser):
    """

----------------------------- Section ---------------------------------

    # http://www.ilgiramondo.net/forum/trentino-alto-adige/

     # URL Topic:
    <a class="title" href="http://www.ilgiramondo.net/forum/trentino-alto-adige/21531-trentino-alto-adige-renon.html"
    id="thread_title_21531">Trentino Alto Adige - Renon</a>

    # Paginetion Topic
    <div id="threadlist" class="threadlist">
        < > ... < >
            <dl class="pagination" id="pagination_threadbit_15753">
                <dt class="label">25 Pagine <span class="separator">&bull;</span></dt>
                        <dd>
                            <span class="pagelinks">
                                 <span>
                <a href="http://www.ilgiramondo.net/forum/trentino-alto-adige/15753-trentino-alto-adige.html">1</a>
                </span> <span><a href="http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/15753-trentino-alto-adige.html">2</a></span> <span><a href="http://www.ilgiramondo.net/forum/page-3/trentino-alto-adige/15753-trentino-alto-adige.html">3</a></span>
                                      ... <a href="http://www.ilgiramondo.net/forum/page-25/trentino-alto-adige/15753-trentino-alto-adige.html">25</a>
                                </span>
                            </dd>
                     </dl>
        < > ... < >
    </div>
    """

    def match(self, url):
    #   found if is a VBulletin section
        logger.info('Check VBulletin section rules of the site: %s', url)
        section_soup = get_soup_from_url(url)
        html = section_soup.find('html')
        if html is not None:
            f_section = section_soup.find('div', {"id": "threadlist"}, {"class": "threadlist"})
            if html.get('id') == 'vbulletin_html' and f_section is not None:
                return True
        else:
            return False

        return False

    def find_topic_url(self, div):
        """
        find how many topic compose this forum section
        """
        for topic in div.find_all('a', {"class": "title"}):
            yield topic.get('href')

    def find_topic_pagination(self, div):
        """
        find if there is a pagination for the topic
        """
        for page in div.find_all('span', {"class": "pagelinks"}): #<span class="pagelinks">
            for url_topic in page.find_all('a'):
                yield url_topic.get('href')

    def find_section_pagination(self, text_soup):
        """
        find if there's pagination in this section
        """
        span_pages = text_soup.find('span', {"class": "selected"})
        if span_pages is not None:
            for url_page in span_pages.find_all('a'):
                yield url_page.get('href')

    def run(self, url):
    #   start VBulletin rules
        logger.info('Run VBulletin section rules of the site: %s', url)
        text_soup = get_soup_from_url(url)
        div_lists = text_soup.find_all('div', {"class": "inner"}) # type list
        for a in self.find_section_pagination(text_soup):
            yield a

        for div in div_lists:
            cnt = 0
            for cnt, url in enumerate(self.find_topic_pagination(div)):
                yield url

            # if no pagination is a single topic, url
            if not cnt:
                for url in self.find_topic_url(div):
                    yield url


class VBulletin_Topic(Parser):
    """
    ----------------------------- Topic ---------------------------------
    <div id="postlist" class="postlist">

    Page 1: http://www.ilgiramondo.net/forum/trentino-alto-adige/6669-trentino-alto-adige-quale-localita.html
    Page 2: http://www.ilgiramondo.net/forum/page-2/trentino-alto-adige/6669-trentino-alto-adige-quale-localita.html

    URL in users' message
    <div class="content">
    <div id="post_message_340346">

    <!-- google_ad_section_start -->
    Io sono stata a Levico Terme a Natale .. c'erano i mercatini, ma mi sembrava carino anche per l'estate.<br />
Non so come sia per la vita serale.. pero' le terme sono carine, c'e' anche la piscina e la sauna nell'hotel.<br />
<a onclick="_gaq.push(['_trackEvent', 'Outgoing', 'www.eden-hotel.com', '']);"
rel="nofollow" href="http://www.eden-hotel.com" target="_blank">www.eden-hotel.com</a><!-- google_ad_section_end -->
    <!-- GAL -->
    </div>
</div>

# Notice: '><!-- google_ad_section_start -->'             '<!-- google_ad_section_end --><!-- GAL -->'

    """

    def match(self, url):
        """
        find if it's a VBulletin topic
        """
        logger.info('Check VBulletin topic rules of the site: %s', url)
        topic_soup = get_soup_from_url(url)
        html = topic_soup.find('html')
        if html is not None:
            f_topic = topic_soup.find('div', {"id": "postlist"}, {"class": "postlist restrain"})
            #        try: # is possible html.get('id') == None
            if html.get('id') == 'vbulletin_html' and f_topic is not None:
                return True
                #        except:
                #            return False

        return False

    def found_pages(self, text_soup):
    #   found by how many pages is composed the topic
    #   <div id="pagination_top" class="pagination_top">
        div_lists = text_soup.find('div', {'id': 'pagination_top'}, {'class': 'pagination_top'})
        for a in div_lists.find_all('a'):
            if a.get('href'):
                yield a.get('href')

    def messages_url(self, text_soup):
    #   found URL in users' messages
        div_lists = text_soup.find_all('div', {"class": "content"}) # type list
        for div in div_lists:
            for a in div.find_all('a'):
                if a.get('href'):
                    yield a.get('href')

    def run(self, url):
    #        run VBulletin section rules
        logger.info('Run VBulletin section rules of the site: %s', url)
        text_soup = get_soup_from_url(url)
        for page_link in self.messages_url(text_soup):
            yield page_link
        for pages in self.found_pages(text_soup):
            yield pages


class GenericLink(Parser):
    """
    Diffbot
    """
    defpath = 'http://www.diffbot.com/api/frontpage'
    s_token = '22df3421e2ecce206e95c4e68b44b9aa'

    def match(self, url):
        return True

    def run(self, url):
        logger.info('Run Diffbot on site: %s', url)
        try:
            xmlanswer = get(self.defpath, self.timeout + 30, params=dict(token=self.s_token, url=url))
        except requests.exceptions.Timeout:
            logger.warning('Invalid URL, Diffbot is taking too long for the answer, skip %s', url)
            return

        try:
            doc = etree.fromstring(xmlanswer.encode('utf-8'))
            for link in doc.iterfind('.//link'):
                yield link.text.strip()
        except etree.ParseError:
            logger.warning('Invalid URL, HTML or Diffbot\'s XML is corrupted , skip %s', url)
            return


class AlLink(Parser):
#    Anlysis on all link of the site
    def match(self, url):
        return True

    def run(self, url):
        logger.info('Run AlLink on site: %s', url)
        text_soup = get_soup_from_url(url)
        a_lists = text_soup.find_all('a') # a list
        for a in a_lists:
            yield a.get('href')
