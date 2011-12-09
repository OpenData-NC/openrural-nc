from django.contrib import admin

from openrural.error_log.models import Error


class ErrorAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'scraper', 'name', 'location', 'zipcode')
    list_filter = ('date', 'name', 'scraper')
    search_fields = ('location', 'description')
admin.site.register(Error, ErrorAdmin)
