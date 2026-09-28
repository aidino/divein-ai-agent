from src.math_service import calculate_discount


def test_discount():
    result = calculate_discount(100000.0, 10.0)
    assert result == 90000.0, f"Kỳ vọng 90000.0 nhưng nhận {result}"
