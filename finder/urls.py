from django.urls import path

from . import views

urlpatterns = [
    path("", views.entry, name="entry"),
    path("<str:market>/", views.finder, name="finder"),
]
