#!/usr/bin/env python

import sys
import datetime
from optparse import OptionParser

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.streets.models import ImproperCity
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
import ebdata.retrieval.log  # sets up base handlers.
# Note there's an undocumented assumption in ebdata that we want to
# put unescape html before putting it in the db.  Maybe wouldn't have
# to do this if we used the scraper framework in ebdata?

from openrural.retrieval.scraperwiki import ScraperWikiScraper

SCHEMA_SLUG = 'corporations'


class Scraper(ScraperWikiScraper):

    scraper_name = "nc_secretary_of_state_corporation_filings"
    list_filter = {'Status': 'Current-Active', 'PrinCounty': 'Orange'}
    ordering = 'DateFormed ASC'

    schema_slugs = ('corporations',)
    has_detail = False

    def save(self, old_record, data, detail_record):
        if old_record is not None:
            self.num_skipped += 1
            return # We already have this inspection.
        date, time = data['DateFormed'].split('T', 1)
        item_date = datetime.datetime.strptime(date, "%Y-%m-%d")
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
        item = self.create_newsitem(
            attrs,
            title=data['CorpName'],
            item_date=item_date,
            location_name=address,
            zipcode=address_parts['zip'],
        )

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['sosid'], record['SOSID'])
            return qs[0]
        except IndexError:
            return None

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
