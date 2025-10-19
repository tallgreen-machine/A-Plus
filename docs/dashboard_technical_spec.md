# A-Plus Trading Bot Dashboard: Technical Specification

## 1. Overview

This document outlines the technical functionality and API endpoints for the A-Plus Trading Bot's web dashboard. The purpose of this dashboard is to provide a real-time monitoring and control interface for the automated trading bot.

The dashboard is a Flask web application that communicates with the bot's backend services and its PostgreSQL database.

## 2. Existing Functionality & API Endpoints

The current dashboard provides a simple, real-time view of the bot's status. The front-end polls the following API endpoints every 5 seconds.

### **GET `/api/portfolio`**

-   **Function:** Retrieves the most recent portfolio status and a list of current asset holdings.
-   **Data Source:** Reads from the `portfolio_history` and `trades` tables in the PostgreSQL database.
-   **JSON Response Example:**
    ```json
    {
      "portfolio": {
        "timestamp": "Sun, 19 Oct 2025 18:30:00 GMT",
        "equity": 10150.50,
        "cash": 7150.50
      },
      "holdings": [
        {
          "symbol": "BTC/USDT",
          "quantity": 0.1
        }
      ]
    }
    ```

### **GET `/api/trades`**

-   **Function:** Retrieves a list of the last 100 trades executed by the bot.
-   **Data Source:** Reads from the `trades` table.
-   **JSON Response Example:**
    ```json
    [
      {
        "id": 1,
        "timestamp": "Sun, 19 Oct 2025 18:30:00 GMT",
        "symbol": "BTC/USDT",
        "direction": "BUY",
        "quantity": 0.1,
        "price": 30000.00,
        "fill_cost": 3000.00
      }
    ]
    ```

### **GET `/api/logs`**

-   **Function:** Retrieves the last 100 lines from the bot's main log file for real-time debugging.
-   **Data Source:** Reads from `/var/log/aplus.log` on the server.
-   **JSON Response Example:**
    ```json
    [
      "INFO:A-Plus:Starting A-Plus Trading Bot...",
      "INFO:A-Plus:Next candle in 59.8s. Sleeping for 61.8s."
    ]
    ```

### **GET & POST `/api/config`**

-   **Function:** Allows reading and updating the bot's configuration. Currently, it only manages the `TIMEFRAMES` setting. A `POST` request to this endpoint will automatically restart the bot service to apply the changes.
-   **Data Source:** Reads from and writes to `/etc/aplus/aplus.env` on the server.
-   **GET Response Example:**
    ```json
    {
      "timeframe": "1m"
    }
    ```
-   **POST Request Body Example:**
    ```json
    {
      "timeframe": "5m"
    }
    ```

## 3. Suggestions for New Features & Visualizations

To create a more powerful and intuitive interface, we recommend the following features.

### **3.1. Historical Equity Curve**

-   **Concept:** A primary chart on the dashboard that plots the portfolio's total equity over time. This is the most important visualization for assessing performance at a glance.
-   **Implementation:** This would require a new API endpoint, `GET /api/portfolio/history`, that retrieves all records from the `portfolio_history` table.
-   **Proposed API Endpoint:** `GET /api/portfolio/history`
-   **JSON Response Example:**
    ```json
    [
      { "timestamp": "Sun, 19 Oct 2025 18:00:00 GMT", "equity": 10000.00 },
      { "timestamp": "Sun, 19 Oct 2025 18:01:00 GMT", "equity": 10010.25 },
      { "timestamp": "Sun, 19 Oct 2025 18:02:00 GMT", "equity": 10005.75 }
    ]
    ```

### **3.2. Key Performance Indicators (KPIs)**

-   **Concept:** A dedicated section to display critical performance metrics calculated from the trade history. This provides a deeper understanding of the strategy's performance beyond the simple equity curve.
-   **Suggested Metrics:**
    *   **Total P/L ($ and %):** Total profit or loss.
    *   **Sharpe Ratio:** Risk-adjusted return.
    *   **Max Drawdown:** The largest peak-to-trough decline in portfolio value.
    *   **Win/Loss Ratio:** The ratio of winning trades to losing trades.
    *   **Average Profit per Trade:** Average dollar amount made on winning trades.
    *   **Average Loss per Trade:** Average dollar amount lost on losing trades.
-   **Implementation:** This would require a new endpoint, `GET /api/performance`, that calculates these metrics from the `trades` and `portfolio_history` tables.

### **3.3. Interactive Candlestick Charts**

-   **Concept:** Instead of a simple table of trades, display an interactive candlestick chart for each traded symbol. The chart should visually mark where `BUY` and `SELL` trades occurred.
-   **Implementation:** This is a more advanced feature. It would require:
    1.  A new API endpoint to fetch historical candle data (e.g., `GET /api/klines?symbol=BTC/USDT&timeframe=1m`).
    2.  A robust charting library on the front-end (e.g., TradingView's Lightweight Charts, Chart.js).
    3.  Overlaying the trade data from the existing `/api/trades` endpoint onto the chart.

### **3.4. Bot Status Indicator**

-   **Concept:** A clear, unambiguous status indicator (e.g., a colored dot or text) that shows whether the bot service is `RUNNING`, `STOPPED`, or has `FAILED`.
-   **Implementation:** This would require a new endpoint, `GET /api/status`, that runs `systemctl status aplus.service` on the server and parses the output.

## 4. Summary for the Designer

-   The dashboard is a data visualization and control tool for a trading bot.
-   The core existing features are viewing portfolio value, holdings, recent trades, and logs.
-   The key user interaction is changing the bot's candle timeframe.
-   Future design should focus on providing deeper performance insights through an equity curve, KPIs, and interactive charts.
-   The overall aesthetic should be clean, data-focused, and suitable for a financial application (e.g., dark theme, clear fonts).

This document should provide a solid foundation for the design process. I have saved it to `docs/dashboard_technical_spec.md`.
