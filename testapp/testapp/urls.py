from django.conf.urls import patterns, include, url
from testapp.api import UserResource
from django.contrib import admin
admin.autodiscover()

user_resource = UserResource()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    (r'^api/', include(user_resource.urls))
)
