from django.conf.urls import patterns, url

# General
#------------------------------------------------------------
urlpatterns = patterns('queue_app.views',
    url(r'^login/$', 'log_in'),
    url(r'^logout/$', 'log_out'),
    url(r'^status/$', 'status'),
)

# LMS-facing interface for queue requests
#------------------------------------------------------------
urlpatterns += patterns('queue_app.lms_interface',
    url(r'^submit/$', 'submit'),
)

# External pulling interface
#------------------------------------------------------------
urlpatterns += patterns('queue_app.ext_interface',
    url(r'^get_queuelen/$', 'get_queuelen'),
    url(r'^get_submission/$', 'get_submission'),
    url(r'^put_result/$', 'put_result'),
)
