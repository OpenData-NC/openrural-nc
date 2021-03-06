from django.db import models

from ebpub.db.models import NewsItem


class GeocodeBatch(models.Model):
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
        verbose_name_plural = 'Geocode Batches'

    def __unicode__(self):
        return "{0} ({1})".format(self.scraper, self.id)


class Geocode(models.Model):
    batch = models.ForeignKey(GeocodeBatch, related_name='geocodes')
    news_item = models.ForeignKey(NewsItem, related_name='geocodes', null=True,
                                  blank=True)
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    scraper = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=1024)
    zipcode = models.CharField(max_length=16, blank=True)
    success = models.BooleanField(default=True)
    name = models.CharField(max_length=255, blank=True, db_index=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        if self.name:
            return "{0}: {1}".format(self.name, self.location)
        else:
            return self.location


# class MessageBatch(models.Model):
#     start_time = models.DateTimeField(auto_now_add=True, db_index=True)

#     class Meta(object):
#         verbose_name_plural = 'Message Batches'

#     def __unicode__(self):
#         return self.start_time


class Message(models.Model):
    # batch = models.ForeignKey(Batch, related_name='message')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    logger = models.CharField(max_length=512, db_index=True)
    level = models.CharField(max_length=16, db_index=True)
    body = models.TextField()
    funcname = models.CharField("Function", max_length=512, blank=True)
    pathname = models.CharField("Path", max_length=2048, blank=True)
    lineno = models.PositiveIntegerField("Line", null=True, blank=True)
