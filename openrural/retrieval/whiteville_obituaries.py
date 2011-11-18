#!/usr/bin/env python

import sys
import logging
import datetime
import feedparser
from optparse import OptionParser

from django.conf import settings
from django.contrib.gis.geos import Point

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema
from ebpub.utils.logutils import log_exception
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
import ebdata.retrieval.log  # sets up base handlers.
# Note there's an undocumented assumption in ebdata that we want to
# put unescape html before putting it in the db.  Maybe wouldn't have
# to do this if we used the scraper framework in ebdata?
from ebdata.retrieval.utils import convert_entities


logger = logging.getLogger('openrural.retrieval.whiteville_obituaries')


class ObituaryScraper(object):

    url = "http://www.whiteville.com/?rss=obituaries"
    geocoder = geocoder.SmartGeocoder()

    def __init__(self, schema_slug='obituaries'):
        NewsItem.objects.all().delete()
        try:
            self.schema = Schema.objects.get(slug=schema_slug)
        except Schema.DoesNotExist:
            logger.error("Schema (%s): DoesNotExist" % schema_slug)
            sys.exit(1)

    def parse_entry(self, entry, title):
        try:
            item = NewsItem.objects.get(title=title, schema__id=self.schema.id)
        except NewsItem.DoesNotExist:
            item = NewsItem(title=title, schema=self.schema)
        description = convert_entities(entry.description)
        try:
            location, description = description.split(' -- ', 1)
        except ValueError:
            logger.error("Unable to parse description: %s", description)
            return
        item.url = entry.link
        item.description = description
        item.pub_date = datetime.datetime(*entry.updated_parsed[:6])
        try:
            item.location_name = self.geocoder.geocode(location)
        except geocoder.DoesNotExist:
            logger.error("Failed to geocode %s" % location)
            item.location_name = location
        created = item.pk is not None
        item.save()
        return created

    def update(self):
        """ Download Calendar RSS feed and update database """
        logger.info("Starting ObituaryScraper")
        feed = feedparser.parse(self.url)
        total_created = 0
        for entry in feed.entries:
            title = convert_entities(entry.title)
            try:
                created = self.parse_entry(entry, title)
                if created:
                    total_created += 1
            except:
                logger.error("unexpected error:", sys.exc_info()[1])
                log_exception()
                break
        logger.info("Created %d of %d total" % (created, len(feed.entries)))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    optparser = OptionParser()
    add_verbosity_options(optparser)
    opts, args = optparser.parse_args(argv)
    setup_logging_from_opts(opts, logger)
    ObituaryScraper().update()


if __name__ == '__main__':
    sys.exit(main())
