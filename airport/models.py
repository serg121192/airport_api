import os
import uuid
from django.utils.text import slugify

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Airport(models.Model):
    name = models.CharField(max_length=255, null=False)
    closest_city = models.CharField(max_length=60, null=False)

    class Meta:
        verbose_name_plural = "airports"

    def __str__(self):
        return f"{self.name} ({self.closest_city})"


class AirplaneType(models.Model):
    name = models.CharField(max_length=255, null=False)

    class Meta:
        verbose_name_plural = "airplane_types"

    def __str__(self):
        return f"Type: {self.name}"


class Crew(models.Model):
    first_name = models.CharField(max_length=60, null=False)
    last_name = models.CharField(max_length=60, null=False)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name_plural = "staff"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


def airplane_path_image(instance: "Airplane", file_name: str) -> str:
    _, extension = os.path.splitext(file_name)
    return (
        f"airplane_images/uploads/{slugify(instance.name)}"
        f"-{uuid.uuid4()}{extension}"
    )


class Airplane(models.Model):
    name = models.CharField(max_length=255, null=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(
        AirplaneType,
        related_name="airplanes",
        on_delete=models.CASCADE,
        blank=True,
    )
    image = models.ImageField(upload_to=airplane_path_image, null=True)

    @property
    def number_of_seats(self):
        return self.rows * self.seats_in_row

    class Meta:
        verbose_name_plural = "airplanes"

    def __str__(self):
        return f"{self.name} (seats: {self.number_of_seats})"


class Route(models.Model):
    source = models.ForeignKey(
        Airport, related_name="routes_from", on_delete=models.CASCADE
    )
    destination = models.ForeignKey(
        Airport, related_name="routes_to", on_delete=models.CASCADE
    )
    distance = models.IntegerField()

    class Meta:
        verbose_name_plural = "routes"
        indexes = [models.Index(fields=["source", "destination"])]

    def __str__(self):
        return f"{self.source} - {self.destination} "


class Flight(models.Model):
    route = models.ForeignKey(
        Route, related_name="flights", on_delete=models.CASCADE
    )
    airplane = models.ForeignKey(
        Airplane, related_name="flights", on_delete=models.CASCADE
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    staff = models.ManyToManyField(Crew, related_name="flights")

    class Meta:
        verbose_name_plural = "flights"
        indexes = [models.Index(fields=["departure_time"])]

    def __str__(self):
        return (
            f"Route: {self.route}, "
            f"Airplane: {self.airplane.name}, "
            f"Departure time: {self.departure_time}, "
            f"Arrival time: {self.arrival_time}"
        )


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.created_at)


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    flight = models.ForeignKey(
        Flight, related_name="tickets", on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        Order, related_name="tickets", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["flight", "row", "seat"], name="unique_seat_on_flight"
            ),
        ]

    @staticmethod
    def validate_seat(seat, row, airplane, err_to_raise):
        for ticket_attr_value, ticket_attr_name, airplane_attr_name in [
            (seat, "seat", "seats_in_row"),
            (row, "row", "rows"),
        ]:
            count_attrs = getattr(airplane, airplane_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise err_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} "
                        f"number must be in available range: "
                        f"(1, {airplane_attr_name}): "
                        f"(1, {count_attrs})"
                    }
                )

    def clean(self):
        Ticket.validate_seat(
            self.seat,
            self.row,
            self.flight.airplane,
            ValidationError,
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(Ticket, self).save(*args, **kwargs)
