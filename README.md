# Portfolio Service MCP Server

A comprehensive Model Context Protocol (MCP) server that integrates popular brokerage APIs for portfolio management, market data access, and trading operations.

## Features

- **Multi-Broker Support**: Seamlessly integrate with multiple brokers
  - Interactive Brokers (IBKR)
  - TradeStation
- **Comprehensive Market Data**: Access to real-time and historical market data
- **Advanced Trading Capabilities**: Execute and manage trades programmatically
- **News Integration**: Get real-time market news and full articles
- **Options Trading Support**: Access options chains and manage options positions
- **TradingView Integration**: Built-in market scanning capabilities

## TradingView Integration

### Market Scanning Tools

1. **tradingview_scan_for_stocks**
   - Execute custom stock screening queries using TradingView's extensive database
   - Access to over 3000 technical and fundamental indicators
   - Flexible query building with SQL-like syntax
   - Example queries:
   ```python
   # Basic stock screening
   Query().select('open', 'high', 'low', 'VWAP', 'MACD.macd', 'RSI')
   
   # Advanced filtering
   Query().select('close', 'volume', 'EMA5', 'EMA20').where(
       Column('close').between(Column('EMA5'), Column('EMA20')),
       Column('type').isin(['stock', 'fund'])
   )
   
   # Complex market scanning
   Query().select('name', 'close', 'volume').where(
       Column('market_cap_basic').between(1_000_000, 50_000_000),
       Column('relative_volume_10d_calc') > 1.2,
       Column('MACD.macd') >= Column('MACD.signal')
   ).order_by('volume', ascending=False)
   ```

2. **tradingview_scan_from_scanner**
   - Use pre-built market scanners
   - Available scanners:
     - premarket_gainers
     - premarket_losers
     - premarket_most_active
     - premarket_gappers
     - postmarket_gainers
     - postmarket_losers
     - postmarket_most_active

## Interactive Brokers (IBKR) Integration

> note: you need to have a running IBKR TWS instance to use these endpoints

### Market Data Tools

1. **ibkr_get_bars** 
   - Get OHLCV (Open, High, Low, Close, Volume) data for stocks and indices
   - Supports multiple timeframes from 1 second to monthly bars
   - Configurable for regular trading hours or extended hours
   - Customizable date ranges and bar sizes
   ```python
   # Example timeframes
   - Bar sizes: "1 min", "5 mins", "1 hour", "1 day", "1 week", "1 month"
   - Durations: "60 S", "30 D", "13 W", "6 M", "10 Y"
   ```

### Order Management Tools

1. **ibkr_place_new_order**
   - Place market or limit orders for stocks
   - Support for both buy and sell orders
   - Optional take profit and stop loss parameters
   - Bracket order capability

2. **ibkr_modify_order**
   - Modify existing orders
   - Update order prices and other parameters
   - Real-time order status tracking

### News Integration

1. **ibkr_get_news_headlines**
   - Fetch recent news headlines for any symbol
   - Configurable time range
   - Multiple news providers support (Dow Jones, Reuters, etc.)

2. **ibkr_get_news_article**
   - Retrieve full article content
   - Direct access to news sources
   - Historical news archive access

### Options Trading Support

1. **ibkr_get_option_expirations**
   - List all available expiration dates for options
   - Support for stock, index, and futures options

2. **ibkr_read_option_chain**
   - Access complete option chains
   - View all strikes and expiration dates
   - Real-time options data

### Account Resources

Access key account information through these endpoints:

1. **brokerage://ibkr/account_summary**
   - Complete account overview
   - Key metrics: Net Liquidation Value, Buying Power, etc.
   - Real-time account updates

2. **brokerage://ibkr/portfolio**
   - Current positions and holdings
   - Real-time position updates
   - Detailed position information

3. **brokerage://ibkr/orders**
   - All trades from current session
   - Comprehensive order history
   - Order status tracking

4. **brokerage://ibkr/open_orders**
   - Active order monitoring
   - Real-time order status
   - Open order management

## Configuration

Configure the server using environment variables:

```bash
# TradeStation Configuration
TRADESTATION_API_KEY="your_api_key"
TRADESTATION_API_SECRET="your_api_secret"
TS_REFRESH_TOKEN="your_refresh_token"
TS_ACCOUNT_ID="your_account_id"

# Interactive Brokers Configuration
IBKR_ACCOUNT_ID="your_account_id"
```

For detailed instructions on obtaining API credentials, visit our [setup guide](https://medium.com/@itay1542/how-to-get-free-historical-intraday-equity-prices-with-code-examples-8f36fc57e1aa).

## Installation

### Claude Desktop Integration

#### MacOS
Configure in: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

#### Windows
Configure in: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "portfolio_service": {
      "command": "uv",
      "args": [
        "--directory",
        "<path_to_project>/portfolio_service",
        "run",
        "portfolio_service"
      ]
    }
  }
}
```

## Development

### Dependencies Management

```bash
# Sync dependencies and update lockfile
uv sync
```

### Debugging

For optimal debugging experience, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
# Launch MCP Inspector
npx @modelcontextprotocol/inspector uv --directory <path_to_project>/portfolio_service run portfolio-service
```

The Inspector provides a web interface for real-time debugging and monitoring of the MCP server.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and feature requests.

## License

This project is open-source and available under the MIT license.