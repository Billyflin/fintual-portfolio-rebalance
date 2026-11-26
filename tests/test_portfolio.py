"""Unit tests for Stock and Portfolio rebalancing behavior."""

from __future__ import annotations

import unittest
from decimal import Decimal

from portfolio_rebalancer import (
    InvalidAllocationError,
    InvalidHoldingError,
    InvalidPriceError,
    MissingPriceError,
    Portfolio,
    Stock,
    TradeAction,
)


class StockTestCase(unittest.TestCase):
    def test_current_price_sets_and_returns_last_available_price(self) -> None:
        aapl = Stock("aapl")
        self.assertEqual(aapl.symbol, "AAPL")

        with self.assertRaises(MissingPriceError):
            aapl.current_price()

        self.assertEqual(aapl.current_price("199.50"), Decimal("199.50"))
        self.assertEqual(aapl.current_price(), Decimal("199.50"))

        self.assertEqual(aapl.current_price(205), Decimal("205"))
        self.assertEqual(aapl.current_price(), Decimal("205"))

    def test_invalid_prices_and_symbols_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Stock("   ")

        stock = Stock("META", price=100)
        for bad_price in (0, -10, "0", "-0.01", "NaN", "Infinity", float("inf"), True, "abc", ""):
            with self.subTest(bad_price=bad_price), self.assertRaises(InvalidPriceError):
                stock.current_price(bad_price)


class PortfolioRebalanceTestCase(unittest.TestCase):
    def test_canonical_meta_40_aapl_60_rebalance_and_cash_neutrality(self) -> None:
        meta = Stock("META", price=500)
        aapl = Stock("AAPL", price=200)

        # Current: 6 META ($3,000 = 60%) + 10 AAPL ($2,000 = 40%) -> $5,000 total
        # Target:  40% META ($2,000 -> 4 sh) + 60% AAPL ($3,000 -> 15 sh)
        portfolio = Portfolio(
            holdings={meta: 6, aapl: 10},
            allocations={meta: Decimal("0.4"), aapl: Decimal("0.6")},
        )

        plan = portfolio.rebalance()
        self.assertEqual(plan.total_value, Decimal("5000"))
        self.assertFalse(plan.is_balanced)
        self.assertEqual(len(plan.orders), 2)

        sell, buy = plan.orders
        self.assertEqual(sell.symbol, "META")
        self.assertEqual(sell.action, TradeAction.SELL)
        self.assertEqual(sell.amount, Decimal("1000"))
        self.assertEqual(sell.shares, Decimal("2"))

        self.assertEqual(buy.symbol, "AAPL")
        self.assertEqual(buy.action, TradeAction.BUY)
        self.assertEqual(buy.amount, Decimal("1000"))
        self.assertEqual(buy.shares, Decimal("5"))

        self.assertEqual(plan.total_sell_amount, plan.total_buy_amount)
        self.assertIn("Portfolio total value: $5000.00", plan.format_summary())

    def test_already_balanced_portfolio_returns_empty_orders(self) -> None:
        meta = Stock("META", price=100)
        aapl = Stock("AAPL", price=100)
        portfolio = Portfolio(
            holdings={meta: 4, aapl: 6},
            allocations={"META": "0.4", "AAPL": "0.6"},
        )

        plan = portfolio.rebalance()
        self.assertTrue(plan.is_balanced)
        self.assertEqual(plan.orders, ())
        self.assertEqual(plan.total_sell_amount, Decimal("0"))
        self.assertEqual(plan.total_buy_amount, Decimal("0"))
        self.assertIn("already balanced", plan.format_summary())

    def test_unallocated_holding_is_fully_liquidated_before_buys(self) -> None:
        meta = Stock("META", price=500)
        aapl = Stock("AAPL", price=200)
        goog = Stock("GOOG", price=100)

        # $5,000 total: 4 META ($2,000), 10 AAPL ($2,000), 10 GOOG ($1,000)
        # Target: 40% META ($2,000), 60% AAPL ($3,000), 0% GOOG (sell all 10 shares)
        portfolio = Portfolio(
            holdings={meta: 4, aapl: 10, goog: 10},
            allocations={meta: Decimal("0.4"), aapl: Decimal("0.6")},
        )

        plan = portfolio.rebalance()
        self.assertEqual([o.action for o in plan.orders], [TradeAction.SELL, TradeAction.BUY])
        self.assertEqual(plan.sells[0].symbol, "GOOG")
        self.assertEqual(plan.sells[0].shares, Decimal("10"))
        self.assertEqual(plan.buys[0].symbol, "AAPL")
        self.assertEqual(plan.buys[0].shares, Decimal("5"))

    def test_new_target_stock_with_zero_initial_shares_is_bought(self) -> None:
        meta = Stock("META", price=250)
        aapl = Stock("AAPL", price=100)

        # Holding only 4 META ($1,000); target is 40% META ($400) + 60% AAPL ($600)
        portfolio = Portfolio(
            holdings={meta: 4},
            allocations={meta: Decimal("0.4"), aapl: Decimal("0.6")},
        )

        plan = portfolio.rebalance()
        self.assertEqual([o.action for o in plan.orders], [TradeAction.SELL, TradeAction.BUY])
        self.assertEqual(plan.sells[0].symbol, "META")
        self.assertEqual(plan.sells[0].shares, Decimal("2.4"))
        self.assertEqual(plan.buys[0].symbol, "AAPL")
        self.assertEqual(plan.buys[0].shares, Decimal("6"))

    def test_price_update_between_calls_changes_rebalance_output(self) -> None:
        meta = Stock("META", price=100)
        aapl = Stock("AAPL", price=100)
        portfolio = Portfolio(
            holdings={meta: 4, aapl: 6},
            allocations={meta: "0.4", aapl: "0.6"},
        )
        self.assertTrue(portfolio.rebalance().is_balanced)

        # META doubles to $200: 4*$200=$800, 6*$100=$600 -> total $1,400
        # Target: 40% META ($560 -> sell $240 = 1.2 sh), 60% AAPL ($840 -> buy $240 = 2.4 sh)
        meta.current_price(200)
        self.assertEqual(portfolio.total_value(), Decimal("1400"))
        plan = portfolio.rebalance()
        self.assertEqual(plan.sells[0].shares, Decimal("1.2"))
        self.assertEqual(plan.buys[0].shares, Decimal("2.4"))

    def test_rebalance_is_pure_and_does_not_mutate_holdings(self) -> None:
        meta = Stock("META", price=500)
        aapl = Stock("AAPL", price=200)
        portfolio = Portfolio(
            holdings={meta: 6, aapl: 10},
            allocations={meta: "0.4", aapl: "0.6"},
        )
        before = portfolio.holdings
        _ = portfolio.rebalance()
        self.assertEqual(portfolio.holdings, before)

    def test_round_trip_applying_orders_reaches_exact_target_weights(self) -> None:
        nvda = Stock("NVDA", price="137.45")
        msft = Stock("MSFT", price="418.12")
        tsla = Stock("TSLA", price="251.33")
        spy = Stock("SPY", price="590.05")

        holdings = {nvda: Decimal("12"), msft: Decimal("5"), tsla: Decimal("9")}
        allocations = {
            nvda: Decimal("0.1"),
            msft: Decimal("0.2"),
            spy: Decimal("0.7"),
        }
        portfolio = Portfolio(holdings=holdings, allocations=allocations)
        plan = portfolio.rebalance()

        # Verify SELLs precede BUYs and cash proceeds match purchases closely.
        seen_buy = False
        for order in plan.orders:
            if order.action is TradeAction.BUY:
                seen_buy = True
            else:
                self.assertFalse(seen_buy, "All SELL orders must precede BUY orders")

        self.assertAlmostEqual(plan.total_sell_amount, plan.total_buy_amount, places=20)

        # Apply orders to simulated post-trade share balances.
        updated_shares = portfolio.holdings
        for order in plan.orders:
            prev = updated_shares.get(order.symbol, Decimal("0"))
            if order.action is TradeAction.SELL:
                updated_shares[order.symbol] = prev - order.shares
            else:
                updated_shares[order.symbol] = prev + order.shares

        self.assertEqual(updated_shares["TSLA"], Decimal("0"))
        post_values = {
            sym: updated_shares[sym] * portfolio.stocks[sym].current_price()
            for sym in ("NVDA", "MSFT", "SPY")
        }
        post_total = sum(post_values.values(), Decimal("0"))
        self.assertAlmostEqual(post_total, plan.total_value, places=20)

        targets = (
            ("NVDA", Decimal("0.1")),
            ("MSFT", Decimal("0.2")),
            ("SPY", Decimal("0.7")),
        )
        for sym, target_wt in targets:
            actual_wt = post_values[sym] / post_total
            self.assertAlmostEqual(actual_wt, target_wt, places=20)

    def test_decimal_precision_handles_0_1_0_2_0_7_floats_without_drift(self) -> None:
        a = Stock("AAA", price=19.99)
        b = Stock("BBB", price=33.33)
        c = Stock("CCC", price=10.01)
        portfolio = Portfolio(
            holdings={a: 10, b: 10, c: 10},
            allocations={a: 0.1, b: 0.2, c: 0.7},
        )
        plan = portfolio.rebalance()
        self.assertEqual(sum(p.target_weight for p in plan.positions), Decimal("1"))

    def test_min_trade_amount_filters_dust_trades(self) -> None:
        meta = Stock("META", price=100)
        aapl = Stock("AAPL", price=100)
        # $1,000 total: $405 META (drift +$5), $595 AAPL (drift -$5)
        portfolio = Portfolio(
            holdings={meta: "4.05", aapl: "5.95"},
            allocations={meta: "0.4", aapl: "0.6"},
        )
        skipped = portfolio.rebalance(min_trade_amount=10)
        self.assertTrue(skipped.is_balanced)

        executed = portfolio.rebalance(min_trade_amount=Decimal("4.99"))
        self.assertEqual(len(executed.orders), 2)

    def test_zero_total_value_portfolio_returns_balanced_plan(self) -> None:
        meta = Stock("META", price=500)
        aapl = Stock("AAPL", price=200)
        portfolio = Portfolio(
            holdings={meta: 0, aapl: 0},
            allocations={meta: "0.4", aapl: "0.6"},
        )
        plan = portfolio.rebalance()
        self.assertEqual(plan.total_value, Decimal("0"))
        self.assertTrue(plan.is_balanced)

    def test_missing_price_raises_on_rebalance(self) -> None:
        meta = Stock("META", price=500)
        aapl = Stock("AAPL")  # No price set yet
        portfolio = Portfolio(
            holdings={meta: 2},
            allocations={meta: "0.5", aapl: "0.5"},
        )
        with self.assertRaises(MissingPriceError):
            portfolio.rebalance()

    def test_invalid_allocations_holdings_and_conflicting_stocks_raise(self) -> None:
        meta = Stock("META", price=100)
        aapl = Stock("AAPL", price=100)
        portfolio = Portfolio(holdings={meta: 5})

        with self.assertRaises(InvalidAllocationError):
            portfolio.rebalance()  # No allocations configured

        with self.assertRaises(InvalidAllocationError):
            portfolio.set_allocations({})

        with self.assertRaises(InvalidAllocationError):
            portfolio.set_allocations({meta: "0.5", aapl: "0.4"})  # Sums to 0.9

        with self.assertRaises(InvalidAllocationError):
            portfolio.set_allocations({meta: "-0.1", aapl: "1.1"})

        with self.assertRaises(InvalidAllocationError):
            portfolio.set_allocations({"UNKNOWN": "1"})

        mixed_duplicate: dict[Stock | str, str] = {meta: "0.5", "meta": "0.5"}
        with self.assertRaises(InvalidAllocationError):
            portfolio.set_allocations(mixed_duplicate)

        with self.assertRaises(InvalidHoldingError):
            portfolio.set_holding(meta, -1)

        with self.assertRaises(InvalidHoldingError):
            portfolio.set_holding(meta, True)

        duplicate_meta = Stock("META", price=200)
        with self.assertRaises(InvalidHoldingError):
            portfolio.set_holding(duplicate_meta, 1)

        with self.assertRaises(InvalidAllocationError):
            portfolio.set_allocations({duplicate_meta: "1"})

        portfolio.set_allocations({meta: "1"})
        with self.assertRaises(InvalidAllocationError):
            portfolio.rebalance(min_trade_amount=-5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
