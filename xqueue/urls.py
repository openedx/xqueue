from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^xqueue/', include('queue_app.urls')),
)
