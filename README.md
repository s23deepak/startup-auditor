# Startup-Auditor

Automated startup analysis for AI/ML engineers targeting AI-first startups.

## Overview

Startup-Auditor is a CLI tool that analyzes AI startup websites and generates comprehensive reports including:

- AI architecture stack detection
- Technology gap analysis
- Contribution proposals
- Confidence scoring for all findings

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd startup-auditor

# Install as editable package
pip install -e .

# Install Playwright browsers
playwright install chromium
```

## Quick Start

```bash
# Analyze a startup website
startup-auditor analyze https://prospectai.com

# View help
startup-auditor --help

# Show version
startup-auditor version
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your Wafer Pass API key:
   ```
   WAFER_PASS_API_KEY=your_actual_key_here
   ```

## Commands

| Command | Description |
|---------|-------------|
| `analyze <url>` | Analyze a startup website |
| `report <id>` | View/regenerate a previous report |
| `config` | Configure API keys and thresholds |
| `version` | Show version information |

## Development

```bash
# Run tests
pytest tests/

# Run linting
ruff check .

# Install with dev dependencies
pip install -e ".[dev]"
```

## Project Structure

```
startup-auditor/
├── src/startup_auditor/    # Main package
│   ├── cli.py              # CLI entry point
│   ├── exit_codes.py       # Exit code constants
│   ├── detectors/          # AI stack detection
│   ├── scrapers/           # Web scraping
│   ├── analyzers/          # Gap analysis
│   └── reporters/          # Report generation
├── tests/                  # Test suite
├── pyproject.toml          # Package configuration
└── .env.example            # Environment template
```

## License

MIT
