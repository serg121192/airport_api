from rest_framework import serializers


class AirportSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, requred=True)
    closest_city = serializers.CharField(max_length=60, requred=True)

    class Meta:
        fields = ["id", "name", "closest_city"]
