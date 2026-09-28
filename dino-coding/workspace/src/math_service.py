# External refactor banner
"""Module xử lý tính toán tài chính."""


def calculate_discount(price: float, discount_percent: float) -> float:
    """Tính giá sau chiết khấu."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Tỉ lệ chiết khấu không hợp lệ")

    discount = price * (discount_percent / 100)
    return price - discount


def format_currency(amount: float) -> str:
    """Định dạng số tiền hiển thị."""
    return f"{amount:,.2f} VNĐ"
