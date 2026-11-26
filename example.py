"""Minimal runnable example matching the Fintual prompt (40% META / 60% AAPL)."""

from __future__ import annotations

from decimal import Decimal

from portfolio_rebalancer import Portfolio, Stock


def main() -> None:
    meta = Stock("META", price=500)
    aapl = Stock("AAPL", price=200)
    goog = Stock("GOOG", price=150)

    # Current holdings: 4 META ($2,000), 10 AAPL ($2,000), 10 GOOG ($1,500) -> $5,500 total
    # Target allocation: 40% META ($2,200), 60% AAPL ($3,300), 0% GOOG (liquidate)
    portfolio = Portfolio(
        holdings={meta: 4, aapl: 10, goog: 10},
        allocations={meta: Decimal("0.40"), aapl: Decimal("0.60")},
    )

    plan = portfolio.rebalance()
    print(plan.format_summary())


if __name__ == "__main__":
    main()
