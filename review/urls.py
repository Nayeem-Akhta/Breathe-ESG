# review/urls.py

from django.urls import path
from .views import (
    EntryListView,
    EntryDetailView,
    ApproveEntryView,
    RejectEntryView,
    FlagEntryView,
    DashboardSummaryView,
)

urlpatterns = [
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard'),
    path('entries/', EntryListView.as_view(), name='entry-list'),
    path('entries/<uuid:entry_id>/', EntryDetailView.as_view(), name='entry-detail'),
    path('entries/<uuid:entry_id>/approve/', ApproveEntryView.as_view(), name='approve-entry'),
    path('entries/<uuid:entry_id>/reject/', RejectEntryView.as_view(), name='reject-entry'),
    path('entries/<uuid:entry_id>/flag/', FlagEntryView.as_view(), name='flag-entry'),
]