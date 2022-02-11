from django.urls import re_path

from submission_queue.ext_interface import (get_queuelen, get_submission,
                                            put_result)
from submission_queue.lms_interface import submit
from submission_queue.views import log_in, log_out, status

# General
# ------------------------------------------------------------
urlpatterns = [
    re_path(r'^login/$', log_in),
    re_path(r'^logout/$', log_out),
    re_path(r'^status/$', status),
]

# LMS-facing interface for queue requests
# ------------------------------------------------------------
urlpatterns += [
    re_path(r'^submit/$', submit),
]

# External pulling interface
# ------------------------------------------------------------
urlpatterns += [
    re_path(r'^get_queuelen/$', get_queuelen),
    re_path(r'^get_submission/$', get_submission),
    re_path(r'^put_result/$', put_result),
]
