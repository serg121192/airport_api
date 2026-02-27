from django.urls import path, include
from rest_framework import routers

from airport.views import (
    AirportViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    CrewViewSet,
    FlightViewSet,
    OrderViewSet,
    RouteViewSet,
)


app_name = "airport"

router = routers.DefaultRouter()

router.register("airports", AirportViewSet)
router.register("airplane_types", AirplaneTypeViewSet)
router.register("airplane", AirplaneViewSet, basename="airplane")
router.register("staff", CrewViewSet, basename="staff")
router.register("flights", FlightViewSet, basename="flights")
router.register("orders", OrderViewSet, basename="orders")
router.register("routes", RouteViewSet, basename="routes")

urlpatterns = [
    path("", include(router.urls)),
]
