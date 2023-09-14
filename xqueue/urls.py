from django.urls import path
from django.urls import include

urlpatterns = [
   path('xqueue/', include('submission_queue.urls')),
]
