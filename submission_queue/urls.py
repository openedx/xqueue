from django.urls import path

from submission_queue.ext_interface import (get_queuelen, get_submission,
                                            put_result)
from submission_queue.lms_interface import submit
from submission_queue.views import log_in, log_out, status

# General
# ------------------------------------------------------------
urlpatterns = [
    path('login/', log_in),
    path('logout/', log_out),
    path('status/', status),
]

# LMS-facing interface for queue requests
# ------------------------------------------------------------
urlpatterns += [
    path('submit/', submit),
]

# External pulling interface
# ------------------------------------------------------------
urlpatterns += [
    path('get_queuelen/', get_queuelen),
    path('get_submission/', get_submission),
    path('put_result/', put_result),
]
