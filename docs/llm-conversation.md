# LLM Collaboration Log

In line with Fintual's Software Engineer application instructions (*"Important: If you use LLMs that's ok, but you must share the conversations"*), this document records how an AI coding assistant was used to design, implement, and test this repository.

- **Candidate:** Billy Martínez (`@Billyflin`)
- **Assistant / Environment:** Antigravity CLI coding assistant (Gemini) running locally on Linux
- **Date:** 2026-11-26
- **Scope note:** The broader workspace session covered reviewing replies to open-source PRs and checking the Fintual Lever job posting; only unrelated private job-search tracking details outside this challenge are omitted here. Below is the complete technical flow for this repository.

---

## 1. Prompt & Context Provided

1. Billy instructed the assistant to proceed with Fintual's take-home challenge after Omar Larré replied to our open-source contribution on `fintual-oss/fintual-clapes#19` (`"dale con la tarea tecnica"`).
2. The assistant fetched the public Lever job description (`https://jobs.lever.co/fintual/9c863695-5fdd-40f3-a907-fc8db1227036`), extracted the exact prompt requirements:
   - `Portfolio` class with a collection of `Stock` instances.
   - Each `Stock` has a `Current Price` method that receives the last available price.
   - `Portfolio` holds target `allocated` `Stock` weights (e.g., `40% META, 60% AAPL`).
   - A `rebalance` method returning which stocks should be sold and which should be bought to reach the target allocation.
   - Documentation/comments explaining the thinking process and trade-offs.
   - Transparency log sharing the LLM conversation.

---

## 2. Architecture & Design Discussion

Together we chose a minimal, zero-dependency **Python 3.11+** package (`portfolio_rebalancer`) optimizing for clarity, financial correctness, and testability over unnecessary framework scaffolding:

1. **Dual read/write `Stock.current_price(price=None)` method:**
   - The prompt states each `Stock` has a method receiving the last available price. Designing `current_price(price=None)` as a single method that updates & stores the price when passed an argument, and returns the cached `Decimal` price when called with `None`, satisfies both direct price updates (`meta.current_price(520)`) and internal price lookups during `portfolio.rebalance()`—failing loudly with `MissingPriceError` if a stock has never been priced.
2. **`decimal.Decimal` everywhere + `bool` guard:**
   - Binary floats introduce rounding errors (e.g., `0.1 + 0.2 != 0.3`). All inputs convert via `to_decimal()`, using `str(value)` for `float` inputs so `0.4` parses as `Decimal("0.4")` and explicitly rejecting `bool` (`isinstance(True, int)` in Python).
3. **Single `Stock` instance identity per ticker:**
   - Because `Stock` prices live on the `Stock` object itself, registering two separate `Stock("AAPL", ...)` instances with different prices for the same ticker could silently cause inconsistent valuations. `Portfolio` guards against conflicting instances for the same normalized uppercase symbol while allowing convenience string keys (e.g., `{"META": "0.4"}`) in `set_allocations()`.
4. **Pure `rebalance()` returning `RebalancePlan` (`SELL` before `BUY`):**
   - Instead of mutating `holdings` during calculation, `rebalance()` returns an immutable `RebalancePlan` containing `positions` (current vs. target weights and values) and `orders` sorted with all `SELL` trades first (generating cash, including 100% liquidation of holdings omitted from `allocations`) followed by `BUY` trades.
   - Full liquidations (`target_weight == 0`) reuse exact held `shares` directly rather than dividing `amount / price` so repeating decimals never leave fractional share dust.
5. **Intentional non-goals:**
   - Fractional shares are assumed; fees, taxes, external cash deposits/withdrawals, and minimum lot rounding are intentionally omitted for scope clarity, while `min_trade_amount` allows skipping negligible dust trades.

---

## 3. Verification Performed

All code and tests were executed and checked locally before publishing:

1. **Unit tests (`unittest`):** 14 test methods covering canonical `40% META / 60% AAPL`, already-balanced portfolios, unallocated full liquidations, new target buys from 0 shares, dynamic price updates via `current_price()`, purity of `rebalance()`, round-trip invariant check ensuring post-trade weights match targets to 20+ decimal places, `0.1/0.2/0.7` float precision, `min_trade_amount` dust filtering, zero-value portfolios, missing prices, and invalid inputs.
2. **Runnable example (`example.py`):** Verified printed positions and `SELL`/`BUY` order summary.
3. **Static analysis:** Verified with `ruff check .` and `mypy --strict portfolio_rebalancer tests example.py`.
