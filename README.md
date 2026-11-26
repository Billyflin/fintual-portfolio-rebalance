# Portfolio Rebalancer

A clean, dependency-free Python module (`>=3.11`) for rebalancing a stock portfolio toward target allocation weights, built for the Fintual Software Engineer challenge.

## Design & Trade-Offs

- **Exact financial arithmetic (`Decimal`)**: Prices, share counts, weights, and trade amounts use `decimal.Decimal` instead of binary `float`. Even common decimal weights such as `0.1 + 0.2 + 0.7` stay exact with zero IEEE-754 drift.
- **`Stock.current_price(price=None)` contract**: Each `Stock` stores its latest available price. Calling `stock.current_price(new_price)` validates (`> 0`, finite, non-boolean) and updates the price; calling `stock.current_price()` reads the last stored price and raises `MissingPriceError` if no price has been set yet.
- **Pure `Portfolio.rebalance()`**: Rebalancing inspects current holdings and latest prices on demand and returns an immutable `RebalancePlan` (`orders`, `positions`, `total_value`, `format_summary()`) without mutating holdings in place. Callers can preview, filter, or persist orders safely.
- **Self-funded execution order (`SELL` before `BUY`)**: Positions currently held above their target weight—including stocks omitted from `allocations` (treated as `0%` target)—emit `SELL` orders before `BUY` orders so sale proceeds fund purchases.
- **Scoped simplicity**: Fractional shares are supported (standard in retail investment apps), and optional dust filtering is exposed via `min_trade_amount`. Taxes, brokerage fees, external cash inflows/outflows, and whole-share lot rounding are intentionally left out of scope to keep the core model concise and clear.

## Project Structure

```text
portfolio_rebalancer/
  __init__.py      Public exports
  exceptions.py    Domain errors (InvalidPriceError, MissingPriceError, InvalidAllocationError, ...)
  stock.py         Stock entity and safe numeric parsing
  portfolio.py     Portfolio, RebalancePlan, RebalanceOrder, PositionSnapshot
tests/
  test_portfolio.py Unit tests (edge cases, invariants, precision, error handling)
example.py         Runnable 40% META / 60% AAPL (+ unallocated stock liquidation) example
docs/
  llm-conversation.md Transparency record of LLM usage during this exercise
```

## Quick Start

Run the runnable example:

```bash
python3 example.py
```

Run the full test suite (standard library only, no third-party dependencies required):

```bash
python3 -m unittest discover -s tests -v
```

Optional static checks (with `ruff` and `mypy` installed):

```bash
ruff check .
mypy --strict portfolio_rebalancer tests example.py
```

## AI / LLM Disclosure

Following Fintual's guidelines (*"If you use LLMs that's ok, but you must share the conversations"*), the design discussion and implementation steps carried out with an AI coding assistant are documented transparently in [`docs/llm-conversation.md`](docs/llm-conversation.md).
