import os
import tempfile
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from airport.models import (
    Airport,
    Airplane,
    AirplaneType,
    Crew,
    Flight,
    Route,
)

from airport.serializers import (
    AirplaneListSerializer,
    AirplaneRetrieveSerializer,
)


AIRPLANE_URL = reverse("airport:airplanes-list")
FLIGHT_URL = reverse("airport:flights-list")


def sample_airport(**params):
    defaults = {"name": "Kyiv", "closest_city": "Kyiv"}
    defaults.update(params)

    return Airport.objects.create(**defaults)


def sample_airplane_type(**params):
    defaults = {"name": "Charter"}
    defaults.update(params)

    return AirplaneType.objects.create(**defaults)


def sample_airplane(**params):
    defaults = {
        "name": "Airbus",
        "rows": 9,
        "seats_in_row": 30,
        "airplane_type": sample_airplane_type(),
    }
    defaults.update(params)

    return Airplane.objects.create(**defaults)


def sample_route(**params):
    defaults = {
        "source": sample_airport(),
        "destination": sample_airport(),
        "distance": 0,
    }
    defaults.update(params)

    return Route.objects.create(**defaults)


def sample_flight(**params):
    route = sample_route()
    airplane = sample_airplane()
    staff = Crew.objects.create(first_name="Keanu", last_name="Reaves")

    defaults = {
        "route": route,
        "airplane": airplane,
        "departure_time": timezone.make_aware(datetime(2026, 3, 10, 14, 0, 0)),
        "arrival_time": timezone.make_aware(datetime(2026, 3, 10, 19, 0, 0)),
    }
    defaults.update(params)

    flight = Flight.objects.create(**defaults)
    flight.staff.add(staff)

    return flight


def image_upload_url(airplane_id):
    return reverse("airport:airplanes-upload-image", args=[airplane_id])


def detail_url(airplane_id):
    return reverse("airport:airplanes-detail", args=[airplane_id])


class UnauthenticatedAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(AIRPLANE_URL)
        print(res.status_code)
        print(res.text)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_user@test.com", "test_user"
        )
        self.client.force_authenticate(self.user)

    def test_airplanes_list(self):
        sample_airplane()
        sample_airplane()

        res = self.client.get(AIRPLANE_URL)

        airplanes = Airplane.objects.order_by("id")
        serializer = AirplaneListSerializer(airplanes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_flights_by_route(self):
        airport_1 = sample_airport(name="Milan", closest_city="Milan")
        airport_2 = sample_airport(name="Madrid", closest_city="Madrid")
        airport_3 = sample_airport(name="Barcelona", closest_city="Barcelona")

        route_1 = sample_route(destination=airport_1, distance=1450)
        route_2 = sample_route(destination=airport_2, distance=1710)
        route_3 = sample_route(destination=airport_3, distance=1520)

        airplane = sample_airplane()

        flight_1 = sample_flight(
            route=route_1,
            airplane=airplane,
        )
        flight_2 = sample_flight(
            route=route_2,
            airplane=airplane,
        )
        flight_3 = sample_flight(
            route=route_3,
            airplane=airplane,
        )

        res = self.client.get(
            FLIGHT_URL, {"routes": f"{route_1.id},{route_2.id}"}
        )
        ids = [f["id"] for f in res.data]

        self.assertIn(flight_1.id, ids)
        self.assertIn(flight_2.id, ids)
        self.assertNotIn(flight_3.id, ids)

    def test_filter_by_airplane(self):
        airport_1 = sample_airport(name="Milan", closest_city="Milan")
        airport_2 = sample_airport(name="Madrid", closest_city="Madrid")

        route_1 = sample_route(
            destination=airport_1,
        )
        route_2 = sample_route(destination=airport_2)

        airplane_1 = sample_airplane()
        airplane_2 = sample_airplane(name="AH 380")

        flight_1 = sample_flight(
            route=route_1,
            airplane=airplane_1,
        )
        flight_2 = sample_flight(
            route=route_2,
            airplane=airplane_2,
        )

        res = self.client.get(FLIGHT_URL, {"airplanes": f"{airplane_2.id}"})
        ids = [f["id"] for f in res.data]

        self.assertIn(flight_2.id, ids)
        self.assertNotIn(flight_1.id, ids)

    def test_filter_by_departure_time(self):
        flight_1 = sample_flight(
            departure_time=timezone.make_aware(datetime(2024, 3, 10, 14, 0, 0))
        )
        flight_2 = sample_flight()

        res = self.client.get(
            FLIGHT_URL, {"departure_time": f"{flight_1.departure_time.date()}"}
        )
        ids = [f["id"] for f in res.data]

        self.assertIn(flight_1.id, ids)
        self.assertNotIn(flight_2.id, ids)

    def test_retrieve_airplane_detail(self):
        plane_type = AirplaneType.objects.create(name="Jet")
        airplane = sample_airplane(airplane_type=plane_type)

        url = detail_url(airplane.id)
        res = self.client.get(url)

        serializer = AirplaneRetrieveSerializer(airplane)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_create_airplane_forbidden(self):
        payload = {
            "name": "AH 380",
            "airplane_type": sample_airplane_type().id,
            "rows": 10,
            "seats_in_row": 3,
        }
        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "adminpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_airplane(self):
        payload = {
            "name": "AH 777",
            "airplane_type": sample_airplane_type().id,
            "rows": 10,
            "seats_in_row": 3,
        }
        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airplane = Airplane.objects.get(id=res.data["id"])
        for key in payload.keys():
            if key == "airplane_type":
                self.assertEqual(payload[key], airplane.airplane_type.id)
            else:
                self.assertEqual(payload[key], getattr(airplane, key))


class AiplaneImageUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@admin.com", "adminpass"
        )
        self.client.force_authenticate(self.user)
        self.airplane = sample_airplane()
        self.flight = sample_flight(airplane=self.airplane)

    def tearDown(self):
        self.airplane.image.delete()

    def test_upload_image_to_airplane(self):
        url = image_upload_url(self.airplane.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.airplane.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.airplane.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.airplane.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_airplane_list_should_not_work(self):
        url = AIRPLANE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "name": "AH 380",
                    "rows": 10,
                    "seats_in_row": 3,
                    "airplane_type": sample_airplane_type().id,
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airplane = Airplane.objects.get(name="AH 380")
        self.assertFalse(airplane.image)

    def test_image_url_is_shown_on_airplane_detail(self):
        url = image_upload_url(self.airplane.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(AIRPLANE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_flight_detail(self):
        url = image_upload_url(self.airplane.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(FLIGHT_URL)

        self.assertIn("airplane_image", res.data[0].keys())

    def test_put_airplane_not_allowed(self):
        payload = {
            "name": "AH 380",
            "rows": 10,
            "seats_in_row": 3,
            "airplane_type": sample_airplane_type().id,
        }

        airplane = sample_airplane()
        url = detail_url(airplane.id)

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_airplane_not_allowed(self):
        airplane = sample_airplane()
        url = detail_url(airplane.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
