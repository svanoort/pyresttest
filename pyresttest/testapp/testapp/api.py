"""
Rest API for basic REST application to use in testing REST testing
And if that ain't meta I don't know what is!
"""
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS
from tastypie import fields
from testapp.models import Person


class PersonResource(ModelResource):
    """ Rest resource for the users"""

    class Meta:
        queryset = Person.objects.all()
        resource_name = 'person'
        authorization = Authorization()
        list_allowed_methods = ['get', 'post']  # List or create single item
        detail_allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        filtering = { #Search by fields
            'id': ALL,
            'login': ALL,
            'first_name': ALL,
            'last_name': ALL
        }
        always_return_data = True  # Allows for POST to return object

