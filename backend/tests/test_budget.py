from tools import calculate_trip_budget


def test_within_budget():
    result = calculate_trip_budget(
        total_budget=1500, nights=4, travellers=2,
        hotel_total=600, flights_total=400, activities_total=100, daily_spend_per_person=30,
    )

    data = result["data"]
    assert data["breakdown"]["food_and_local_transport"] == 300  # 30 * 2 people * 5 days
    assert data["estimated_total"] == 1400
    assert data["remaining"] == 100
    assert data["within_budget"] is True
    assert data["per_person"] == 700


def test_over_budget():
    data = calculate_trip_budget(total_budget=500, nights=2, travellers=1, hotel_total=450, flights_total=200)["data"]

    assert data["within_budget"] is False
    assert data["remaining"] == -150


def test_negative_amount_rejected():
    result = calculate_trip_budget(total_budget=1000, nights=2, travellers=1, hotel_total=-5)

    assert result == {"status": "error", "error_message": "hotel_total must not be negative."}
