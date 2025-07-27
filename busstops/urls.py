from django.apps import apps
from django.contrib.sitemaps.views import index, sitemap
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_control
from django.views.generic.base import RedirectView, TemplateView

from buses.utils import cdn_cache_control
from bustimes.urls import urlpatterns as bustimes_views
from disruptions.urls import urlpatterns as disruptions_urls
from fares import mytrip
from fares import views as fares_views
from fares.urls import urlpatterns as fares_urls
from vehicles.urls import urlpatterns as vehicles_urls
from vosa.urls import urlpatterns as vosa_urls
from django.urls import path
from .views import change_notes_view

from . import views

sitemaps = {
    "operators": views.OperatorSitemap,
    "services": views.ServiceSitemap,
}

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="index.html"),
        name="index",
    ),
    path(
        "/goon",
        TemplateView.as_view(template_name="goon.html"),
        name="goon",
    ),
    path(
        "satellites/all",
        TemplateView.as_view(template_name="satellites_all.html"),
        name="all_satellites",
    ),
    path(
        "satellites",
        TemplateView.as_view(template_name="satellites_home.html"),
        name="satellites",
    ),
    path(
        "satellites/starlink",
        TemplateView.as_view(template_name="starlink_satellites.html"),
        name="sl_satellites",
    ),
    path(
        "satellites/oneweb",
        TemplateView.as_view(template_name="oneweb_satellites.html"),
        name="ow_satellites",
    ),
    path(
        "satellites/gps",
        TemplateView.as_view(template_name="gps_satellites.html"),
        name="gps_satellites",
    ),
    path(
        "satellites/visual",
        TemplateView.as_view(template_name="visual_satellites.html"),
        name="visual_satellites",
    ),
    path(
        "satellites/weather",
        TemplateView.as_view(template_name="weather_satellites.html"),
        name="weather_satellites",
    ),
    path(
        "satellites/goes",
        TemplateView.as_view(template_name="goes_satellites.html"),
        name="goes_satellites",
    ),
    path(
        "satellites/kuiper",
        TemplateView.as_view(template_name="kuiper_satellites.html"),
        name="kuiper_satellites",
    ),
    path(
        "satellites/soon",
        TemplateView.as_view(template_name="satellites_soon.html"),
        name="coming_soon_sat",
    ),
    path(
        "ads.txt",
        cache_control(max_age=1800)(
            RedirectView.as_view(
                url="https://cdn.transportthing.uk/ads.txt"
            )
        ),
    ),
    path("discord", RedirectView.as_view(url="https://discord.gg/JAjNUJWdVD")),
    path("version", views.version),
    path("contact", views.contact, name="contact"),
    path(
        "cookies",
        cdn_cache_control(1800)(TemplateView.as_view(template_name="cookies.html")),
    ),
    path(
        "privacy",
        cdn_cache_control(1800)(TemplateView.as_view(template_name="cookies.html")),
    ),
    path("503", TemplateView.as_view(template_name="503.html")),
    path("trains", TemplateView.as_view(template_name="trains.html")),
    path("maintenance", TemplateView.as_view(template_name="maintenance.html")),
    path("data", TemplateView.as_view(template_name="data.html")),
    path("status", views.status),
    path("timetable-source-stats.json", views.timetable_source_stats),
    path("stats.json", views.stats),
    path("robots.txt", views.robots_txt),
    path("stops.json", views.stops_json),
    path(
        "region/<pk>",
        cdn_cache_control(1800)(views.RegionDetailView.as_view()),
        name="region_detail",
    ),
    re_path(
        r"^(admin-)?area/(?P<pk>\d+)",
        cdn_cache_control(1800)(views.AdminAreaDetailView.as_view()),
        name="adminarea_detail",
    ),
    path(
        "districts/<int:pk>",
        views.DistrictDetailView.as_view(),
        name="district_detail",
    ),
    re_path(
        r"^localities/(?P<pk>[ENen][Ss]?[0-9]+)",
        cdn_cache_control(1800)(views.LocalityDetailView.as_view()),
    ),
    path(
        "localities/<slug>",
        cdn_cache_control(1800)(views.LocalityDetailView.as_view()),
        name="locality_detail",
    ),
    path(
        "stops/<pk>",
        cdn_cache_control(30)(views.StopPointDetailView.as_view()),
        name="stoppoint_detail",
    ),
    path("stations/<pk>", views.StopAreaDetailView.as_view(), name="stoparea_detail"),
    path(
        "stops/<slug:atco_code>/departures",
        views.stop_departures,
    ),
    re_path(r"^operators/(?P<pk>[A-Z]+)$", views.OperatorDetailView.as_view()),
    path(
        "operators/<slug>",
        views.OperatorDetailView.as_view(),
        name="operator_detail",
    ),
    path("operators/<slug>/tickets", mytrip.operator_tickets, name="operator_tickets"),
    path("operators/<slug>/tickets/<uuid:id>", mytrip.operator_ticket),
    path(
        "services/<int:service_id>.json",
        views.service_map_data,
        name="service_map_data",
    ),
    path(
        "services/<int:service_id>/timetable",
        views.service_timetable,
        name="service_timetable",
    ),
    path(
        "services/<int:service_id>/timetable.csv",
        views.service_timetable_csv,
    ),
    path(
        "services/<slug>",
        views.ServiceDetailView.as_view(),
        name="service_detail",
    ),
    path("services/<slug>/fares", fares_views.service_fares),
    path("sitemap.xml", cache_control(max_age=3600)(index), {"sitemaps": sitemaps}),
    path(
        "sitemap-<section>.xml",
        cache_control(max_age=3600)(sitemap),
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("search-query", views.search, name="search"),
    path("journey", views.journey),
    path(
        ".well-known/change-password",
        RedirectView.as_view(url="/accounts/password_change/"),
    ),
    path("fares/", include(fares_urls)),
]

urlpatterns += bustimes_views + disruptions_urls + vehicles_urls + vosa_urls


if apps.is_installed("debug_toolbar"):
    import debug_toolbar

    urlpatterns += [
        path("__debug__", include(debug_toolbar.urls)),
    ]


urlpatterns += [
    path('updates', change_notes_view, name='changes.html'),
]
