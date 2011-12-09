from django.db import models


class Error(models.Model):
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    scraper = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=1024)
    zipcode = models.CharField(max_length=16, blank=True)
    description = models.TextField()
