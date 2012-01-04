import pprint
from collections import defaultdict

from django.core.management.base import BaseCommand

from ebdata.parsing import dbf


class Command(BaseCommand):
    help = 'Inspect .dbf files'

    def handle(self, *args, **options):
        dbf_file = args[0]
        needle = int(args[1])
        db = self.load_db(dbf_file)
        if needle in db:
            pprint.pprint(db[needle])

    def load_db(self, dbf_file, rel_key='TLID'):
        db = defaultdict(list)
        with open(dbf_file, 'rb') as f:
            for row in dbf.dict_reader(f, strip_values=True):
                db[row[rel_key]].append(row)
        return db
