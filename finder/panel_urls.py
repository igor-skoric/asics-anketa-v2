from django.urls import path

from . import panel_views

urlpatterns = [
    path("", panel_views.home, name="panel_home"),
    path("prijava/", panel_views.login_view, name="panel_login"),
    path("odjava/", panel_views.logout_view, name="panel_logout"),
    path("nalozi/", panel_views.users_view, name="panel_users"),
    path("nalozi/<int:user_id>/", panel_views.user_active, name="panel_user_active"),
    path("nalozi/<int:user_id>/trzista/", panel_views.user_markets, name="panel_user_markets"),
    path("<str:market>/", panel_views.shoe_list, name="panel_shoes"),
    path("<str:market>/izvoz.xlsx", panel_views.catalog_export, name="panel_catalog_export"),
    path("<str:market>/uvoz/", panel_views.catalog_import, name="panel_catalog_import"),
    path("<str:market>/uvoz/pregled/", panel_views.catalog_import_preview, name="panel_catalog_import_preview"),
    path("<str:market>/nova/", panel_views.shoe_edit, name="panel_shoe_new"),
    path("<str:market>/<int:shoe_id>/", panel_views.shoe_edit, name="panel_shoe"),
    path("<str:market>/<int:shoe_id>/obrisi/", panel_views.shoe_delete, name="panel_shoe_delete"),
]
