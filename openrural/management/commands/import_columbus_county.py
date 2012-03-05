import os
import datetime
import tempfile

from optparse import make_option, OptionParser

from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import DataSource, OGRGeomType, OGRGeometry
from ebpub.utils.text import slugify

from ebpub.db.models import Location, LocationType
from ebpub.metros.allmetros import get_metro
from ebpub.utils.geodjango import make_multi
from ebpub.geocoder.parser.parsing import normalize
from ebpub.utils.script_utils import die, makedirs, wget, unzip


class Command(BaseCommand):
    help = 'Import Columbus County city boundaries'
    url = 'http://www.columbusco.org/GISData/City.zip'

    def clean_name(self, name):
        # convert "BRUNSWICK CITY LIMITS" to "BRUNCSWICK"
        return unicode(name).replace(' CITY LIMITS', '')

    def download_file(self):
        tmp = tempfile.mkdtemp()
        wget(self.url, cwd=tmp) or die("Could not download %s" % self.url)
        zip_path = os.path.join(tmp, 'City.zip')
        unzip(zip_path, cwd=tmp) or die("failed to unzip %s" % tmp)
        shapefile = os.path.join(tmp, 'City.shp')
        return shapefile

    def handle(self, **options):
        shapefile = self.download_file()
        now = datetime.datetime.now()
        metro_name = get_metro()['metro_name'].upper()
        # get or create City location type
        type_data = {'name': 'City', 'plural_name': 'Cities', 'slug': 'cities',
                     'is_browsable': True, 'is_significant': True,
                     'scope': metro_name}
        try:
            type_ = LocationType.objects.get(slug=type_data['slug'])
        except LocationType.DoesNotExist:
            type_ = LocationType.objects.create(**type_data)
        # start with a fresh list of cities
        Location.objects.filter(location_type=type_).delete()
        # build list of cities
        locations = {}
        layer = DataSource(shapefile)[0]
        for feature in layer:
            name = self.clean_name(feature['Name'])
            # convert to 4326
            geom = feature.geom.transform(4326, True).geos
            if name not in locations:
                locations[name] = {
                    'name': name,
                    'slug': slugify(name),
                    'location_type': type_,
                    'city': metro_name,
                    'source': 'Columbus County GIS data',
                    'is_public': True,
                    'creation_date': now,
                    'last_mod_date': now,
                    'display_order': 0,
                    'normalized_name': normalize(name),
                    'location': [],
                }
            location = locations[name]
            location['location'].append(geom)
        # create city locations
        for name, location in locations.iteritems():
            location['location'] = make_multi(location['location'])
            Location.objects.create(**location)
        print 'Imported %d locations' % type_.location_set.count()
