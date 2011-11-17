#   Copyright 2011 OpenPlans and contributors
#
#   This file is part of OpenBlock
#
#   OpenBlock is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   OpenBlock is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with OpenBlock.  If not, see <http://www.gnu.org/licenses/>.
#


# Based on http://wiki.github.com/dkukral/everyblock/install-everyblock

from django.core.management.base import BaseCommand
from ebpub.utils.script_utils import die, makedirs, wget, unzip
import os
import tempfile

class Command(BaseCommand):
    help = 'Import NC streets & blocks for the given county to ebpub.'

    def handle(self, county, **options):
        # First we download a bunch of zipfiles of TIGER data.
        TMP = tempfile.mkdtemp()
        os.chdir(TMP)
        print 'Download TIGER data to %s' % TMP
        OUTDIR = os.path.join(TMP, 'tiger_data')
        BASEURL= 'ftp://ftp2.census.gov/geo/tiger/TIGER2010'
        STATE = '37' # NC
        ZIPS = ("PLACE/2010/tl_2010_%s_place10.zip" % STATE,
                "EDGES/tl_2010_%s_edges.zip" % county,
                "FACES/tl_2010_%s_faces.zip" % county,
                "FEATNAMES/tl_2010_%s_featnames.zip" % county,
                )
        makedirs(OUTDIR) or die("couldn't create directory %s" % OUTDIR)
        for fname in ZIPS:
            wget('%s/%s' % (BASEURL, fname), cwd=OUTDIR) or die(
                "Could not download %s/%s" % (BASEURL, fname))

        import glob
        for fname in glob.glob(os.path.join(OUTDIR, '*zip')):
            unzip(fname, cwd=OUTDIR) or die("Could not unzip %s" % fname)
        print "Shapefiles unzipped in %s" % OUTDIR

        # Now we load them into our blocks table.
        from ebpub.streets.blockimport.tiger import import_blocks
        from ebpub.utils.geodjango import get_default_bounds
        print "Importing blocks, this may take several minutes ..."

        # Passing --city means we skip features labeled for other cities.

        importer = import_blocks.TigerImporter(
            '%s/tl_2010_%s_edges.shp' % (OUTDIR, county),
            '%s/tl_2010_%s_featnames.dbf' % (OUTDIR, county),
            '%s/tl_2010_%s_faces.dbf' % (OUTDIR, county),
            '%s/tl_2010_%s_place10.shp' % (OUTDIR, STATE),
            encoding='utf8',
            filter_bounds=get_default_bounds())
        num_created = importer.save()
        print "Created %d blocks" % num_created

        #########################

        print "Populating streets and fixing addresses, these can take several minutes..."

        # Note these scripts should be run ONCE, in this order,
        # after you have imported *all* your blocks.

        from ebpub.streets.bin import populate_streets
        populate_streets.main(['-v', '-v', '-v', '-v', 'streets'])
        populate_streets.main(['-v', '-v', '-v', '-v', 'block_intersections'])
        populate_streets.main(['-v', '-v', '-v', '-v', 'intersections'])
        print "Done."

        print "Removing temp directory %s" % TMP
        os.system('rm -rf %s' % TMP)
