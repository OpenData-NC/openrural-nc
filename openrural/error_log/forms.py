from django import forms

from ebpub import geocoder

from openrural.error_log.models import Geocode


class GeocodeForm(forms.ModelForm):

    class Meta(object):
        model = Geocode

    def clean_location(self):
        location = self.cleaned_data['location']
        smart_geocoder = geocoder.SmartGeocoder()
        try:
            self.cleaned_data['result'] = smart_geocoder.geocode(location)
        except geocoder.GeocodingException, e:
            raise forms.ValidationError(unicode(e))
        return location
