# Indian AI Hedge Fund

## Overview

This project implements an AI-powered hedge fund system focused on the Indian stock market. It uses machine learning algorithms and financial data analysis to make informed trading decisions and portfolio management strategies.

## Features

- Real-time market data analysis
- AI-driven trading strategies
- Portfolio optimization
- Risk management system
- Performance analytics dashboard
- Automated trading execution

## Prerequisites

- Python 3.8+
- Poetry (https://python-poetry.org/)
- Access to Indian stock market data APIs
- Required API keys and credentials

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/indian-ai-hedge-fund.git
cd indian-ai-hedge-fund
```

2. Install dependencies using Poetry:

```bash
poetry install
```

## Configuration

1. Create a `.env` file in the root directory
2. Add your API keys and configuration:

```
API_KEY=your_api_key
SECRET_KEY=your_secret_key
```

## Usage

1. Start the system using Poetry:

```bash
poetry run python src/indian_ai_hedge_fund/main.py
```

2. Access the dashboard at `http://localhost:3000`

## Project Structure

```
indian-ai-hedge-fund/
├── src/
│   └── indian_ai_hedge_fund/ # Main application source code
│       ├── analysts/         # AI analyst agents
│       ├── llm/              # Language model integrations
│       ├── prompts/          # Prompt templates
│       ├── tools/            # Tools for agents
│       └── utils/            # Utility functions
│       └── main.py           # Main entry point
├── tests/                    # Unit and integration tests
├── docs/                     # Documentation (if any)
├── logs/                     # Log files
├── .env                      # Environment variables (needs creation)
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── pyproject.toml            # Project metadata and dependencies (Poetry)
└── poetry.lock               # Exact dependency versions (Poetry)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading in financial markets carries significant risks. Always consult with financial advisors before making investment decisions.

## Contact

For questions and support, please open an issue in the GitHub repository.
