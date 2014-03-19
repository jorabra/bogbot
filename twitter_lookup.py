import requests
import lxml.html

class TwitterLookup(object):

    def compose_meta(self, url):
        document = self._retrieve_document(url)
        if document is not None:
            fullname, username, tweet = self._parse(document)
            return "%s (@%s): %s" % (fullname, username, tweet)
        else:
            return

    def _retrieve_document(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return

    def _parse(self, document):
        try:
            tree = lxml.html.fromstring(document)
            fullname = tree.xpath('//strong[contains(@class, "fullname")]/text()')[0]
            username = tree.xpath('//span[contains(@class, "username")]/b/text()')[0]
            tweet = tree.xpath('//p[contains(@class, "tweet-text")]')[0].text_content()
            return fullname, username, tweet
        except:
            return

