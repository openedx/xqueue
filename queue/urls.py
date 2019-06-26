from __future__ import absolute_import
from queue.ext_interface import get_queuelen, get_submission, put_result
from queue.lms_interface import submit
from queue.views import log_in, log_out, status

from django.conf.urls import url

# General
# ------------------------------------------------------------
urlpatterns = [
    url(r'^login/$', log_in),
    url(r'^logout/$', log_out),
    url(r'^status/$', status),
]

# LMS-facing interface for queue requests
# ------------------------------------------------------------
urlpatterns += [
    url(r'^submit/$', submit),
]

# External pulling interface
# ------------------------------------------------------------
urlpatterns += [
    url(r'^get_queuelen/$', get_queuelen),
    url(r'^get_submission/$', get_submission),
    url(r'^put_result/$', put_result),
]
