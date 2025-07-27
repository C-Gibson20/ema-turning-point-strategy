# EMA Turning Point Strategy

<p>The EmaTurningPointStrategy is a cryptocurrency trading algorithm developed for the QuantConnect platform and its algorithm framework. This project is specifically designed to trade Bitcoin (BTCUSD) based on exponential moving average (EMA) turning points. The strategy aims to identify potential buying and selling opportunities by analyzing EMA trends and price movements, dynamically adjusting to market conditions.</p>
<br>

## Strategy Overview

The algorithm identifies potential buy/sell signals by detecting local minima and maxima in the short-term EMA, combined with price action analysis and volatility-adjusted thresholds. It incorporates behavioral heuristics to refine entry and exit decisions.
<br>

## Features

* **Asset:** Bitcoin (BTCUSD)
* **Resolution:** Daily
* **Alpha Model:** Custom turning point detection using EMA slope
* **Portfolio Construction:** Insight-weighted target sizing
* **Execution Model:** Immediate execution with commission-awareness
* **Risk Management:** 5% maximum drawdown limit
* **Charting:** Visual plots for trade actions
<br>

## Implementation

### 1. **EMA Turning Point Detection**

* Computes a 3-period EMA with a 6-day rolling window.
* Detects turning points (local minima or maxima) using first derivatives:

  * `MIN`: EMA slope changes from negative to positive.
  * `MAX`: EMA slope changes from positive to negative.
  * `NONE`: No significant change.

### 2. **Volatility-Based Threshold**

* Uses a 6-period ATR to compute a dynamic threshold.
* Trades are only triggered when the price movement exceeds this threshold.

### 3. **Alpha Model**

* Emits `Insight.Up` for buys and `Insight.Down` for sells.
* Recognizes behavioral edge cases:

  * **FOMO BUY**: Price recovers significantly after a SELL.
  * **JOMO SELL**: Price drops sharply after a BUY.

### 4. **Portfolio Construction**

* Allocates 97.5% of available cash for long positions.
* Fully exits on sell signals.

### 5. **Execution Model**

* Executes market orders only if price movement exceeds twice the estimated round-trip fees (0.2% total).
* Filters out unprofitable trades.

### 6. **Risk Management**

* Limits cumulative drawdown to 5% of portfolio value.
<br>

## Visualization

The algorithm plots the following on a custom chart:

* EMA values
* Benchmark (BTCUSD price)
* Trade markers for BUY, SELL, FOMO BUY, and JOMO SELL
