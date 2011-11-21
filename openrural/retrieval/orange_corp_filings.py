#!/usr/bin/env python

import re
import sys
import csv
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


SCHEMA_SLUG = 'corporations'


class Scraper(BaseScraper):

    geocoder = geocoder.AddressGeocoder()
    logname = 'corporation'
    url = 'http://www.secretary.state.nc.us/Corporations/SearchChgs.aspx'

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        super(Scraper, self).__init__(*args, **kwargs)
        if clear:
            self._create_schema()
        self.schema = Schema.objects.get(slug=SCHEMA_SLUG)
        self.num_added = 0
        self.num_total = 0

    def post(self, county, from_date, to_date):
        """ Scrape secretary site for download file -- not working yet """
        # first get the initial page and serialize all form elements
        f = urllib2.urlopen(self.url)
        self.logger.debug('Grabbing initial page to serialize form elements')
        soup = BeautifulSoup(f.read())
        data = {}
        for tag in soup.findAll("input"):
            data[tag.get("name")] = tag.get("value")
        # update the POST data with the needed filter values
        data.update({'County': county, 'From': from_date, 'To': to_date})
        # POST the data and look for a .txt href extension
        f = urllib2.urlopen(self.url, urllib.urlencode(data))
        self.logger.debug('Submitting form and searching for download file')
        soup = BeautifulSoup(f.read())
        anchor = soup.find(href=re.compile("\.txt$"))
        href = anchor.get('href')
        self.logger.debug('Found download file: {0}'.format(href))

    def update(self, filename):
        with open(filename, 'rb') as f:
            reader = csv.reader(f, delimiter='\t')
            reader.next() # skip header
            for row in reader:
                self.parse_row(row)
                self.num_total += 1
        self.logger.info('Added {0} of {1}'.format(self.num_added,
                                                   self.num_total))

    def parse_row(self, row):
        date, time = row[1].split(' ', 1)
        item_date = datetime.datetime.strptime(date, "%m/%d/%Y")
        attrs = {
            'citizenship': row[2],
            'type': row[3],
            'sosid': row[5],
            'agent': row[6],
        }
        address_parts = {
            'line1': row[14],
            'line2': row[15],
            'city': row[16],
            'state': row[17],
            'zip': row[18],
        }
        if address_parts['line1'] == 'None':
            self.logger.debug("{0} has no address, skipping".format(*row))
            return
        if address_parts['line2']:
            address_parts['line1'] = address_parts['line2']
        address = "{line1} {line2}".format(**address_parts)
        try: 
            self.create_newsitem(
                attrs,
                title=row[0],
                item_date=item_date,
                location_name=address,
                zipcode=address_parts['zip'],
            )
        except (geocoder.GeocodingException, geocoder.ParsingError,
                ImproperCity) as e:
            message = "{0} - {1}".format(type(e).__name__, e)
            self.logger.error(message)

    def geocode(self, location_name, zipcode):
        location = self.geocoder.geocode(location_name)
        return location

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
    if len(args) != 2:
        parser.error("Please specify a CSV file to import")
    filename = args[1]
    scraper.update(filename)


if __name__ == '__main__':
    sys.exit(main())
