from django.contrib import admin

from openrural.error_log.models import Error, Batch


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


class ErrorAdmin(admin.ModelAdmin):
    list_display = ('id', 'batch', 'date', 'name', 'location',
                    'zipcode')
    list_filter = ('date', 'name', 'scraper', 'zipcode')
    search_fields = ('batch__id', 'location', 'description')
    ordering = ('-date',)
admin.site.register(Error, ErrorAdmin)
