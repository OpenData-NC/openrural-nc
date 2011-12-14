from django.db import models


class Batch(models.Model):
    scraper = models.CharField(max_length=255, db_index=True)
    start_time = models.DateTimeField(auto_now_add=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True, db_index=True)
    num = models.PositiveIntegerField(default=0)
    num_added = models.PositiveIntegerField(default=0)
    num_changed = models.PositiveIntegerField(default=0)
    num_skipped = models.PositiveIntegerField(default=0)
    num_geocoded = models.PositiveIntegerField(default=0)
    num_geocoded_success = models.PositiveIntegerField(default=0)

    class Meta(object):
        verbose_name_plural = 'Batches'

    def __unicode__(self):
        return "{0} ({1})".format(self.scraper, self.id)


class Error(models.Model):
    batch = models.ForeignKey(Batch, related_name='errors')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    scraper = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=1024)
    zipcode = models.CharField(max_length=16, blank=True)
    description = models.TextField()

    def __unicode__(self):
        return "{0}: {1}".format(self.name, self.location)
