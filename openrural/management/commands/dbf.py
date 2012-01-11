import pprint
from optparse import make_option
from collections import defaultdict

from django.core.management.base import BaseCommand

from ebdata.parsing import dbf


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-g", "--group", action="store", type="string",
                    dest="group"),
        make_option("-f", "--field", action="store", type="string",
                    dest="field", default='TLID'),
    )
    help = 'Inspect .dbf files'

    def handle(self, *args, **options):
        dbf_file = args[0]
        needle = args[1]
        try:
            needle = int(needle)
        except:
            pass
        db = self.load_db(dbf_file, options)
        if needle in db:
            pprint.pprint(db[needle])

    def load_db(self, dbf_file, options):
        if options['group']:
            db = defaultdict(dict)
        else:
            db = defaultdict(list)
        with open(dbf_file, 'rb') as f:
            for row in dbf.dict_reader(f, strip_values=True):
                if options['group']:
                    db[row[options['field']]][row[options['group']]] = row
                else:
                    db[row[options['field']]].append(row)
        return db
