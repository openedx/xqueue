from django.conf.urls import include, url

urlpatterns = [
    url(r'^xqueue/', include('submission_queue.urls')),
]
