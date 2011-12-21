from django.db import models
from django.contrib import admin

from openrural.error_log.models import Geocode, Batch
from openrural.error_log.forms import GeocodeForm, GoogleMapsLink


class BatchAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'scraper', 'end_time', 'num', 'num_added',
                    'num_changed', 'num_skipped', 'num_geocoded',
                    'num_geocoded_success', 'geocode_rate')
    list_filter = ('start_time', 'scraper')
    search_fields = ('batch__id', 'location', 'description')
    ordering = ('-start_time',)

    def geocode_rate(self, obj):
        if obj.num_geocoded > 0:
            rate = float(obj.num_geocoded_success) / obj.num_geocoded
        else:
            rate = 0.0
        return '{0:.2%}'.format(rate)

admin.site.register(Batch, BatchAdmin)


class GeocodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'batch', 'date', 'success', 'location', 'name',
                    'zipcode')
    list_filter = ('success', 'date', 'name', 'scraper', 'zipcode')
    search_fields = ('batch__id', 'location', 'description')
    ordering = ('-date',)
    readonly_fields = ('success', 'name', 'batch', 'news_item', 'scraper',
                       'zipcode')
    form = GeocodeForm
    formfield_overrides = {
        models.CharField: {'widget': GoogleMapsLink},
    }
    def save_model(self, request, obj, form, change):
        obj.news_item.location = form.cleaned_data['result']['point']
        obj.news_item.save()
        obj.name = ''
        obj.success = True
        obj.save()

admin.site.register(Geocode, GeocodeAdmin)
