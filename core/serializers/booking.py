"""
Booking serializers for OIUEEI.
"""

from datetime import date

from rest_framework import serializers

from core.models.booking import BookingPeriod


class BookingPeriodSerializer(serializers.ModelSerializer):
    """Full booking period serializer (for owner view)."""

    class Meta:
        model = BookingPeriod
        fields = [
            "booking_code",
            "booking_created",
            "thing_code",
            "thing_type",
            "requester_code",
            "requester_email",
            "owner_code",
            "start_date",
            "end_date",
            "delivery_date",
            "quantity",
            "status",
        ]
        read_only_fields = [
            "booking_code",
            "booking_created",
            "thing_code",
            "thing_type",
            "requester_code",
            "requester_email",
            "owner_code",
            "status",
        ]


class BookingPeriodCalendarSerializer(serializers.ModelSerializer):
    """Calendar view serializer (limited info for guests)."""

    class Meta:
        model = BookingPeriod
        fields = [
            "start_date",
            "end_date",
            "status",
        ]


class BookingPeriodOwnerCalendarSerializer(serializers.ModelSerializer):
    """Calendar view serializer for owner (includes requester info)."""

    class Meta:
        model = BookingPeriod
        fields = [
            "booking_code",
            "requester_code",
            "start_date",
            "end_date",
            "status",
        ]


class ThingRequestWithDatesSerializer(serializers.Serializer):
    """Serializer for thing request with dates (LEND/RENT/SHARE)."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate_start_date(self, value):
        """Validate that start_date is today or in the future."""
        if value < date.today():
            raise serializers.ValidationError("Start date must be today or in the future")
        return value

    def validate(self, data):
        """Validate date range."""
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError(
                    {"end_date": "End date must be on or after start date"}
                )
        return data


class ThingOrderSerializer(serializers.Serializer):
    """Serializer for ORDER_THING requests (delivery_date + quantity)."""

    delivery_date = serializers.DateField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)

    def validate_delivery_date(self, value):
        """Validate that delivery_date is today or in the future."""
        if value < date.today():
            raise serializers.ValidationError("Delivery date must be today or in the future")
        return value


class MyBookingSerializer(serializers.ModelSerializer):
    """Serializer for user's own booking requests."""

    class Meta:
        model = BookingPeriod
        fields = [
            "booking_code",
            "booking_created",
            "thing_code",
            "thing_type",
            "owner_code",
            "start_date",
            "end_date",
            "delivery_date",
            "quantity",
            "status",
        ]
