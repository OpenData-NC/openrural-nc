#!/usr/bin/env python

import re
import sys
import csv
import json
import urlparse
import urllib
import urllib2
import datetime
import traceback
from optparse import OptionParser

from BeautifulSoup import BeautifulSoup, SoupStrainer

from django.conf import settings
from django.contrib.gis.geos import Point
from django.template import defaultfilters as filters

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.streets.models import ImproperCity
from ebpub.utils.logutils import log_exception
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
import ebdata.retrieval.log  # sets up base handlers.
from ebdata.retrieval.scrapers.base import BaseScraper
# Note there's an undocumented assumption in ebdata that we want to
# put unescape html before putting it in the db.  Maybe wouldn't have
# to do this if we used the scraper framework in ebdata?
from ebdata.retrieval.utils import convert_entities


from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper


SCHEMA_SLUG = 'corporations'


class ScraperWiki(NewsItemListDetailScraper):

    url = "https://api.scraperwiki.com/api/1.0/datastore/sqlite"
    list_filter = None
    ordering = None
    limit = 50

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        super(ScraperWiki, self).__init__(*args, **kwargs)
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

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['sosid'], record['SOSID'])
            return qs[0]
        except IndexError:
            return None


class Scraper(ScraperWiki):

    scraper_name = "nc_secretary_of_state_corporation_filings"
    list_filter = {'Status': 'Current-Active', 'PrinCounty': 'Orange'}
    ordering = 'DateFormed DESC'

    schema_slugs = ('corporations',)
    has_detail = False

    def save(self, old_record, data, detail_record):
        if old_record is not None:
            return # We already have this inspection.
        date, time = data['DateFormed'].split(' ', 1)
        item_date = datetime.datetime.strptime(date, "%m/%d/%Y")
        attrs = {
            'citizenship': data['Citizenship'],
            'type': data['Type'],
            'sosid': data['SOSID'],
            'agent': data['RegAgent'],
        }
        address_parts = {
            'line1': data['PrinAddr1'],
            'line2': data['PrinAddr2'],
            'city': data['PrinCity'],
            'state': data['PrinState'],
            'zip': data['PrinZip'],
        }
        if address_parts['line1'] == 'None':
            self.logger.debug("{0} has no address, skipping".format(*data))
            return
        if address_parts['line2']:
            address_parts['line1'] = address_parts['line2']
        address = "{line1} {line2}".format(**address_parts)
        try: 
            self.create_newsitem(
                attrs,
                title=data['CorpName'],
                item_date=item_date,
                location_name=address,
                zipcode=address_parts['zip'],
            )
        except (geocoder.GeocodingException, geocoder.ParsingError,
                ImproperCity) as e:
            message = "{0} - {1}".format(type(e).__name__, e)
            self.logger.error(message)

    def _create_schema(self):
        try:
            Schema.objects.get(slug=SCHEMA_SLUG).delete()
        except Schema.DoesNotExist:
            pass
        schema = Schema.objects.create(
            name='Corporation',
            plural_name='corporations',
            slug=SCHEMA_SLUG,
            last_updated=datetime.datetime.now(),
            is_public=True,
            indefinite_article='a',
            has_newsitem_detail=True,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Type",
            pretty_name_plural="Types",
            real_name='varchar01',
            name='type',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Registered Agent",
            pretty_name_plural="Registered Agents",
            real_name='varchar02',
            name='agent',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Citizenship",
            pretty_name_plural="Citizenships",
            real_name='varchar03',
            name='citizenship',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="SOSID",
            pretty_name_plural="SOSIDs",
            real_name='int01',
            name='sosid',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    scraper = Scraper(clear=opts.clear)
    setup_logging_from_opts(opts, scraper.logger)
    scraper.update()


if __name__ == '__main__':
    sys.exit(main())
