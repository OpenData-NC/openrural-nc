#!/usr/bin/env python

import sys
import csv
import logging
import datetime
import traceback
from optparse import OptionParser

from django.conf import settings
from django.contrib.gis.geos import Point
from django.template import defaultfilters as filters

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.utils.logutils import log_exception
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
import ebdata.retrieval.log  # sets up base handlers.
from ebdata.retrieval.scrapers.base import BaseScraper
# Note there's an undocumented assumption in ebdata that we want to
# put unescape html before putting it in the db.  Maybe wouldn't have
# to do this if we used the scraper framework in ebdata?
from ebdata.retrieval.utils import convert_entities


logger = logging.getLogger('openrural.retrieval.whiteville_resturants')

SCHEMA_SLUG = 'restaurant-inspections'
ESTABLISHMENT_TYPE_CODES = {
    '1': '*Restaurants (including Drink Stand)',
    '2': '*Food Stands',
    '3': '*Mobile Food Units',
    '4': '*Pushcarts',
    '5': '*Private School Lunchrooms',
    '6': '*Educational Food Service',
    '9': '*Elderly Nutrition Sites (catered)',
    '11': '*Public School Lunchrooms',
    '12': '*Elderly Nutrition Sites (food prepared on premises)',
    '14': '*Limited Food Service',
    '15': '*Commissary for Pushcarts & Mobile Food Units',
    '16': 'Institutional Food Service',
    '20': '*Lodging',
    '21': '*Bed and Breakfast Home',
    '22': '*Summer Camps',
    '23': '*Bed and Breakfast Inn',
    '24': '**Primitive Camp',
    '25': '***Primitive Camp',
    '26': 'Resident Camps',
    '30': '*Meat Markets',
    '40': 'Rest/Nursing Homes',
    '41': 'Hospitals',
    '42': 'Child Day Care',
    '43': 'Residential Care (excluding Foster Homes)',
    '44': 'School Building (private & Public)',
    '45': 'Local Confinement',
    '46': 'Private Boarding Schools/College',
    '47': "Orphanage, Children's Home or Similar Institution",
    '48': 'Adult Day Service',
    '50': 'Seasonal Swimming Pools',
    '51': 'Seasonal Wading Pools',
    '52': 'Seasonal Spas',
    '53': 'Year-Round Swimming Pools',
    '54': 'Year-Round Wading Pools',
    '55': 'Year-Round Spas',
    '61': 'Tattoo',
    '73': 'Temporary Food Establishments',
}


class RestaurantInspections(BaseScraper):

    schema_slug = 'restaurant-inspections'
    geocoder = geocoder.SmartGeocoder()

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        super(RestaurantInspections, self).__init__(*args, **kwargs)
        if clear:
            self._create_schema()
        self.schema = Schema.objects.get(slug=SCHEMA_SLUG)
        self.num_added = 0

    def update(self, filename):
        with open(filename, 'rb') as f:
            reader = csv.reader(f)
            reader.next() # skip header
            for row in reader:
                self.parse_row(row)

    def parse_row(self, row):
        title = filters.title(row[1])
        item_date = datetime.datetime.strptime(row[9], "%m/%d/%Y")
        attrs = {
            'restaurant_id': row[0],
            'restaurant_name': title,
            'status_code': row[8],
            'score': int(float(row[10])*100),
            'form_item_id': row[11],
            'form_item_desc': row[12],
            'activity_item_id': row[13],
            'activity_item_comment': row[14],
        }
        address = "%s, %s, %s %s" % (filters.title(row[3]),
                                     filters.title(row[4]), row[5], row[6])
        # try: 
        self.create_newsitem(
            attrs,
            title=title,
            item_date=item_date,
            location_name=address,
            zipcode=row[6],
        )
        # except:
        #     message = "Error storing inspection for %s: %s" % (row,traceback.format_exc())
        #     self.logger.error(message)

    def geocode(self, location_name, zipcode):
        location = self.geocoder.geocode(location_name)
        return location

    def _create_schema(self):
        try:
            Schema.objects.get(slug=SCHEMA_SLUG).delete()
        except Schema.DoesNotExist:
            pass
        NewsItem.objects.all().delete()
        schema = Schema.objects.create(
            name='Restaurant Inspection',
            plural_name='Restaurant Inspections',
            slug=SCHEMA_SLUG,
            last_updated=datetime.datetime.now(),
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Restaurant Name",
            pretty_name_plural="Restaurant Names",
            real_name='varchar01',
            name='name',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Restaurant ID",
            pretty_name_plural="Restaurant IDs",
            real_name='int01',
            name='resaurant_id',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Score",
            pretty_name_plural="Scores",
            real_name='int02',
            name='score',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Form Item ID",
            pretty_name_plural="Form Item IDs",
            real_name='int03',
            name='form_item_id',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Form Item Description",
            pretty_name_plural="Form Item Descriptions",
            real_name='varchar02',
            name='form_item_desc',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Activity Item Point",
            pretty_name_plural="Activity Item Points",
            real_name='int04',
            name='activity_item_points',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Activity Item Comment",
            pretty_name_plural="Activity Item Comments",
            real_name='varchar03',
            name='activity_item_comment',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Status Code",
            pretty_name_plural="Status Codes",
            real_name='varchar04',
            name='status_code',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    setup_logging_from_opts(opts, logger)
    if len(args) != 2:
        parser.error("Please specify a CSV file to import")
    filename = args[1]
    RestaurantInspections(clear=opts.clear).update(filename)


if __name__ == '__main__':
    sys.exit(main())
