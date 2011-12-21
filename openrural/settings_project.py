"""
Copy this to settings.py, uncomment the various settings, and
edit them as desired.
"""

from ebpub.settings_default import *

########################
# CORE DJANGO SETTINGS #
########################

ADMINS = (
    ('Open Rural Team', 'openrural-team@caktusgroup.com'),
)

MANAGERS = ADMINS

DEBUG = True
TIME_ZONE = 'US/Eastern'

PROJECT_DIR = os.path.normpath(os.path.dirname(__file__))
INSTALLED_APPS = (
    'openrural',
    'openrural.error_log',
    'gunicorn',
    'seacucumber',
) + INSTALLED_APPS
TEMPLATE_DIRS = (os.path.join(PROJECT_DIR, 'templates'), ) + TEMPLATE_DIRS
ROOT_URLCONF = 'openrural.urls'

DATABASES = {
    'default': {
        'NAME': 'openblock_openrural',
        'USER': 'openblock',
        'PASSWORD': 'openblock',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'OPTIONS': {},
        'HOST': '',
        'PORT': '',
        'TEST_NAME': 'test_openblock',
    },
}

#########################
# CUSTOM EBPUB SETTINGS #
#########################

# The domain for your site.
EB_DOMAIN = 'localhost'

# Set both of these to distinct, secret strings that include two instances
# of '%s' each. Example: 'j8#%s%s' -- but don't use that, because it's not
# secret.  And don't check the result in to a public code repository
# or otherwise put it out in the open!
PASSWORD_CREATE_SALT = '%s%s'
PASSWORD_RESET_SALT = '%s%s'

# You probably don't need to override this, the setting in settings.py
# should work out of the box.
#EB_MEDIA_ROOT = '' # necessary for static media versioning.

EB_MEDIA_URL = '' # leave at '' for development


# This is used as a "From:" in e-mails sent to users.
GENERIC_EMAIL_SENDER = 'openblock@' + EB_DOMAIN

# Filesystem location of scraper log.
SCRAPER_LOGFILE_NAME = '/tmp/scraperlog_openrural'

# If this cookie is set with the given value, then the site will give the user
# staff privileges (including the ability to view non-public schemas).
STAFF_COOKIE_NAME = ''
STAFF_COOKIE_VALUE = ''

# What LocationType to redirect to when viewing /locations.
DEFAULT_LOCTYPE_SLUG='neighborhoods'

# What kinds of news to show on the homepage.
# This is one or more Schema slugs.
HOMEPAGE_DEFAULT_NEWSTYPES = [u'news-articles']

# How many days of news to show on the homepage, place detail view,
# and elsewhere.
DEFAULT_DAYS = 7

# Edit this if you want to control where
# scraper scripts will put their HTTP cache.
# (Warning, don't put it in a directory encrypted with ecryptfs
# or you'll likely have "File name too long" errors.)
HTTP_CACHE = '/tmp/openblock_scraper_cache_openrural'

CACHES = {
    # Use whatever Django cache backend you like;
    # FileBasedCache is a reasonable choice for low-budget, memory-constrained
    # hosting environments.
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/openrural_cache'
          # # Use this to disable caching.
          #'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

