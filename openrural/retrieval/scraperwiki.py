
import json
import urllib
import urllib2
import logging

import ebdata.retrieval.log  # sets up base handlers.
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper

logging.getLogger().setLevel(logging.DEBUG)

class ScraperWikiScraper(NewsItemListDetailScraper):

    url = "http://api.scraperwiki.com/api/1.0/datastore/sqlite"
    list_filter = None
    ordering = None
    limit = 50

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        super(ScraperWikiScraper, self).__init__(*args, **kwargs)
        if clear:
            self._create_schema()
        self.num_added = 0
        self.num_total = 0

    def get_query(self, select='*', limit=10, offset=0):
        where = ''
        if self.list_filter:
            parts = []
            for key, val in self.list_filter.iteritems():
                parts.append("{0} = '{1}'".format(key, val))
            where = ' AND '.join(parts)
        query = ['SELECT {0} FROM `swdata`'.format(select)]
        if where:
            query.append('WHERE {0}'.format(where))
        if self.ordering:
            query.append('ORDER BY {0}'.format(self.ordering))
        if limit > 0:
            query.append('LIMIT {0}'.format(limit))
        if offset > 0:
            query.append('OFFSET {0}'.format(offset))
        query = ' '.join(query)
        self.logger.debug(query)
        return query

    def get_url(self, query):
        args = {'name': self.scraper_name, "format": "jsondict",
                "query": query}
        url = "{0}?{1}".format(self.url, urllib.urlencode(args))
        self.logger.info(url)
        return self.get_html(url)

    def count(self):
        query = self.get_query(select='COUNT(*) AS count', limit=0, offset=0)
        data = json.loads(self.get_url(query=query))[0]
        return data['count']

    def list_pages(self):
        count = self.count()
        offset = 0
        while offset < count:
            yield self.get_url(query=self.get_query(limit=self.limit, offset=offset))
            offset += self.limit

    def parse_list(self, data):
        for row in json.loads(data):
            yield row
