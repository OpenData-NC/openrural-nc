import urllib

from django import forms
from django.utils.safestring import mark_safe

from ebpub import geocoder

from openrural.error_log.models import Geocode


__all__ = ('GoogleMapsLink', 'GeocodeForm')


class GoogleMapsLink(forms.TextInput):

    def render(self, name, value, attrs=None):
        html = super(GoogleMapsLink, self).render(name, value, attrs=None)
        location = urllib.urlencode({'q': value})
        link = "http://maps.google.com/maps?{0}".format(location)
        html += "&nbsp;&nbsp;<a href='{0}'>Google Map</a>".format(link)
        return mark_safe(html)


class GeocodeForm(forms.ModelForm):

    class Meta(object):
        model = Geocode

    def clean_location(self):
        location = self.cleaned_data['location']
        smart_geocoder = geocoder.SmartGeocoder()
        try:
            self.cleaned_data['result'] = smart_geocoder.geocode(location)
        except geocoder.InvalidBlockButValidStreet, e:
            raise forms.ValidationError('InvalidBlockButValidStreet')
        except (geocoder.GeocodingException, geocoder.ParsingError), e:
            raise forms.ValidationError(unicode(e))
        return location
