from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ingest/', include('ingestion.urls')),
    path('api/review/', include('review.urls')),
]