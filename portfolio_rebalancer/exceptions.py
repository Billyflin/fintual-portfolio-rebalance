"""Domain exceptions for portfolio rebalancing."""

from __future__ import annotations


class PortfolioError(Exception):
    """Base exception for all portfolio management errors."""


class InvalidPriceError(PortfolioError, ValueError):
    """Raised when a stock price is missing, non-finite, or non-positive."""


class MissingPriceError(PortfolioError, ValueError):
    """Raised when a stock's current price is requested before being set."""


class InvalidHoldingError(PortfolioError, ValueError):
    """Raised when a holding quantity or stock registration is invalid."""


class InvalidAllocationError(PortfolioError, ValueError):
    """Raised when target portfolio allocations are malformed or do not sum to 1."""
