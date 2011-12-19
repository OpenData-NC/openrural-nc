from django.conf import settings
from django.contrib.gis.geos import Point

from geopy import geocoders
from geopy.geocoders.google import GQueryError

from ebpub.geocoder import Geocoder, DoesNotExist


class GoogleGeocoder(Geocoder):

    def __init__(self, *args, **kwargs):
        kwargs['use_cache'] = False # haven't implemented cache yet
        super(GoogleGeocoder, self).__init__(*args, **kwargs)
        self.geocoder = geocoders.Google(settings.GOOGLE_MAPS_API_KEY)

    def _do_geocode(self, location_string):
        try:
            place, (lat, lng) = self.geocoder.geocode(location_string)
        except (GQueryError, ValueError), e:
            raise DoesNotExist(unicode(e))
        location = {'point': Point(lng, lat)}
        return location
