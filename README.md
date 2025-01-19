# Portfolio Service Monorepo

A comprehensive suite of Model Context Protocol (MCP) servers for portfolio management, market data access, and trading operations, organized as a UV workspace.

## Repository Structure

```
portfolio_service/
├── brokerage_service/     # Order execution and portfolio management
├── market_data_service/   # Market data and technical analysis
├── research_service/      # Market research and screening
├── common/               # Shared utilities and libraries
├── pyproject.toml        # Workspace root configuration
└── uv.lock              # Shared lockfile for all workspace members
```

## Development Setup

This repository uses UV workspaces to manage multiple interconnected packages. Each service is a separate package that shares common dependencies and utilities.

### Prerequisites

- Python 3.11+
- [UV](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/itay1542/brokers-mcp.git portfolio_service
cd portfolio_service
```

2. Install dependencies for all workspace members:
```bash
uv sync
```

3. Run a specific service:
```bash
# Run the brokerage service
uv run --package brokerage_service python src/server.py

# Run the market data service
uv run --package market_data_service python src/server.py

# Run the research service
uv run --package research_service python src/server.py
```

### Environment Configuration

Create a `.env` file in each service directory with the required credentials:

```bash
# TradeStation Configuration (market_data_service)
TRADESTATION_API_KEY="your_api_key"
TRADESTATION_API_SECRET="your_api_secret"
TS_REFRESH_TOKEN="your_refresh_token"
TS_ACCOUNT_ID="your_account_id"

# Interactive Brokers Configuration (shared)
IBKR_ACCOUNT_ID="your_account_id"
IBKR_CLIENT_ID="1"
IBKR_HOST="127.0.0.1"
IBKR_PORT="7496"
```

## Services Overview

### Brokerage Service
- Order execution and management
- Portfolio tracking
- Account management
- Position monitoring

### Market Data Service
- Real-time and historical market data
- Technical analysis
- News integration
- Options chain data

### Research Service
- TradingView market scanning
- Custom stock screening
- Technical indicator analysis
- Market research tools

## Common Features

### Interactive Brokers (IBKR) Integration
> Note: Requires a running IBKR TWS instance

- Market data access
- Order management
- News integration
- Options trading support
- Account monitoring

### TradingView Integration

Market scanning capabilities with:
- Custom screening queries
- Pre-built scanners
- Technical indicator analysis
- Fundamental data access

## Development Tools

### Debugging

Use the MCP Inspector for real-time debugging:

```bash
# Debug a specific service
npx @modelcontextprotocol/inspector uv run --package market_data_service python src/server.py
```

### Testing

Run tests for a specific package:
```bash
uv run --package common pytest
```

### Adding Dependencies

Add dependencies to a specific service:
```bash
uv add --package market_data_service pandas
```

## Claude Desktop Integration

Configure in the appropriate location for your OS:

### MacOS
`~/Library/Application\ Support/Claude/claude_desktop_config.json`

### Windows
`%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "brokerage_service": {
      "command": "uv",
      "args": [
        "--directory",
        "<path_to_portfolio_service>",
        "run",
        "--package",
        "brokerage_service",
        "python",
        "brokerage_service/src/server.py"
      ],
      "env": {
        "IBKR_ACCOUNT_ID": "your_account_id",
        "IBKR_CLIENT_ID": "1",
        "IBKR_HOST": "127.0.0.1",
        "IBKR_PORT": "7496",
        "TRADESTATION_API_KEY": "your_api_key",
        "TRADESTATION_API_SECRET": "your_api_secret",
        "TS_REFRESH_TOKEN": "your_refresh_token",
        "TS_ACCOUNT_ID": "your_account_id",
        "IBKR_CLIENT_ID": "1",
      }
    },
    "market_data_service": {
      "command": "uv",
      "args": [
        "--directory",
        "<path_to_portfolio_service>",
        "run",
        "--package",
        "market_data_service",
        "python",
        "market_data_service/src/server.py"
      ],
      "env": {
        "TRADESTATION_API_KEY": "your_api_key",
        "TRADESTATION_API_SECRET": "your_api_secret",
        "TS_REFRESH_TOKEN": "your_refresh_token",
        "TS_ACCOUNT_ID": "your_account_id",
        "IBKR_ACCOUNT_ID": "your_account_id",
        "IBKR_CLIENT_ID": "2",
        "IBKR_HOST": "127.0.0.1",
        "IBKR_PORT": "7496",
      }
    },
    "research_service": {
      "command": "uv",
      "args": [
        "--directory",
        "<path_to_portfolio_service>",
        "run",
        "--package",
        "research_service",
        "python",
        "research_service/src/server.py"
      ]
    }
  }
}
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests across all affected packages
4. Submit a pull request
