from openrural.settings_project import *

#########################
# CUSTOM EBPUB SETTINGS #
#########################

# This is the short name for your city, e.g. "chicago".
SHORT_NAME = 'whiteville'

# Where to center citywide maps, eg. on homepage.
DEFAULT_MAP_CENTER_LON = -78.700562
DEFAULT_MAP_CENTER_LAT = 34.3389
DEFAULT_MAP_ZOOM = 13

# Metros. You almost certainly only want one dictionary in this list.
# See the configuration docs for more info.
METRO_LIST = (
    {
        # Extent of the region, as a longitude/latitude bounding box.
        'extent': (-79.305094, 34.567047, -78.080075, 33.865161),

        # Whether this region should be displayed to the public.
        'is_public': True,

        # Set this to True if the region has multiple cities.
        # You will also need to set 'city_location_type'.
        'multiple_cities': True,

        # The major city in the region.
        'city_name': 'Whiteville',

        # The SHORT_NAME in the settings file.
        'short_name': SHORT_NAME,

        # The name of the region, as opposed to the city (e.g., "Miami-Dade" instead of "Miami").
        'metro_name': 'Columbus County',

        # USPS abbreviation for the state.
        'state': 'NC',

        # Full name of state.
        'state_name': 'North Carolina',

        # Time zone, as required by Django's TIME_ZONE setting.
        'time_zone': TIME_ZONE,

        # Slug of an ebpub.db.LocationType that represents cities.
        # Only needed if multiple_cities = True.
        'city_location_type': 'cities',
    },
)

