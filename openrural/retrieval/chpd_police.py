#!/usr/bin/env python

import sys
import datetime
from optparse import OptionParser

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema, SchemaField, Lookup
from ebpub.streets.models import ImproperCity
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
import ebdata.retrieval.log  # sets up base handlers.
# Note there's an undocumented assumption in ebdata that we want to
# put unescape html before putting it in the db.  Maybe wouldn't have
# to do this if we used the scraper framework in ebdata?

from openrural.retrieval.scraperwiki import ScraperWikiScraper

SCHEMA_SLUG = 'police_reports'

class Scraper(ScraperWikiScraper):

    scraper_name = "chapel_hill_police_reports"
    list_filter = {}
    ordering = 'date DESC'

    schema_slugs = [SCHEMA_SLUG]
    has_detail = False

    def _parse_date(self, date_):
        return datetime.datetime.strptime(date_, '%Y-%m-%dT%H:%M:%S')

    def save(self, old_record, data, detail_record):
        if old_record is not None:
            return # We already have this inspection.
        item_date = self._parse_date(data['date'])
        if not data['location']:
            self.logger.debug("{0} has no address, skipping".format(*data))
            return
        title = data['incident_type']
        # try to find a more specific title, if available:
        for var in ['charge', 'primary_offense']:
            if data[var]:
                title = data[var]
                break
        data['incident_type'] = Lookup.objects.get_or_create_lookup(self.schema_fields['incident_type'], data['incident_type']).pk
        self.create_newsitem(
            data,
            title=title,
            item_date=item_date,
            location_name=data['location'],
            state='NC',
            city='Chapel Hill',
        )

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            date = self._parse_date(record['date'])
            qs = qs.by_attribute(self.schema_fields['date'], date)
            return qs[0]
        except IndexError:
            return None

    def _create_schema(self):
        try:
            Schema.objects.get(slug=SCHEMA_SLUG).delete()
        except Schema.DoesNotExist:
            pass
        schema = Schema.objects.create(
            name='Police Report',
            plural_name='police reports',
            slug=SCHEMA_SLUG,
            last_updated=datetime.datetime.now(),
            is_public=True,
            indefinite_article='a',
            has_newsitem_detail=True,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Incident Type",
            pretty_name_plural="Incident Types",
            real_name='varchar01',
            name='incident_type',
            is_lookup=True,
            is_filter=True,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Charge",
            pretty_name_plural="Charges",
            real_name='varchar02',
            name='charge',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Arrestee",
            pretty_name_plural="Arrestees",
            real_name='varchar03',
            name='arrestee',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Primary Offense",
            pretty_name_plural="Primary Offenses",
            real_name='varchar04',
            name='primary_offense',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Case Number",
            pretty_name_plural="Case Numbers",
            real_name='int01',
            name='case_num',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Date and Time",
            pretty_name_plural="Date and Times",
            real_name='datetime01',
            name='date',
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
