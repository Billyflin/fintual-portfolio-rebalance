"""Stock representation and exact numeric parsing helpers."""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation

from .exceptions import InvalidPriceError, MissingPriceError

Numeric = Decimal | int | float | str


def to_decimal(
    value: Numeric,
    *,
    field_name: str,
    error_cls: type[ValueError] = ValueError,
) -> Decimal:
    """Convert a numeric input to a finite ``Decimal`` without binary float drift.

    Booleans are explicitly rejected because ``bool`` is a subclass of ``int`` in
    Python. Floats are converted via ``str(value)`` so inputs like ``0.4`` parse as
    ``Decimal("0.4")`` rather than ``Decimal("0.40000000000000002220...")``.
    """
    if isinstance(value, bool):
        raise error_cls(f"{field_name} cannot be a boolean")

    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, int):
        parsed = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise error_cls(f"{field_name} must be finite, got {value!r}")
        parsed = Decimal(str(value))
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise error_cls(f"{field_name} cannot be empty")
        try:
            parsed = Decimal(stripped)
        except InvalidOperation as exc:
            raise error_cls(f"Invalid numeric value for {field_name}: {value!r}") from exc
    else:
        raise error_cls(f"Unsupported type for {field_name}: {type(value).__name__}")

    if not parsed.is_finite():
        raise error_cls(f"{field_name} must be finite, got {value!r}")

    return parsed


class Stock:
    """Represents a tradable equity ticker with its last available market price."""

    def __init__(self, symbol: str, price: Numeric | None = None) -> None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Stock symbol must be a non-empty string")
        self._symbol = symbol.strip().upper()
        self._last_price: Decimal | None = None
        if price is not None:
            self.current_price(price)

    @property
    def symbol(self) -> str:
        """Normalized uppercase ticker symbol."""
        return self._symbol

    def current_price(self, price: Numeric | None = None) -> Decimal:
        """Update and return the last available price, or read the cached price.

        Calling ``stock.current_price(price)`` stores the latest market price after
        verifying that it is strictly positive. Calling ``stock.current_price()`` with
        no arguments returns the most recently stored price, raising
        ``MissingPriceError`` if none has been provided yet.
        """
        if price is None:
            if self._last_price is None:
                raise MissingPriceError(f"No current price has been set for stock {self._symbol!r}")
            return self._last_price

        parsed = to_decimal(
            price,
            field_name=f"price for {self._symbol}",
            error_cls=InvalidPriceError,
        )
        if parsed <= Decimal("0"):
            raise InvalidPriceError(
                f"Price for {self._symbol} must be strictly positive, got {parsed}"
            )
        self._last_price = parsed
        return parsed

    def __repr__(self) -> str:
        if self._last_price is None:
            return f"Stock(symbol={self._symbol!r})"
        return f"Stock(symbol={self._symbol!r}, current_price={str(self._last_price)!r})"
