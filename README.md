# TQRS - Ticket Quality Review System

AI-powered ServiceNow ticket quality review system that automates the evaluation of incident tickets using a hybrid rules + LLM approach.

## Features

- **Automated Scoring**: 70-point evaluation across multiple criteria
- **Three Templates**: Incident Logging, Incident Handling, Customer Service
- **AI-Powered Analysis**: OpenAI GPT-4o for nuanced quality assessment
- **Professional Reports**: HTML reports with score gauges and coaching recommendations
- **Batch Processing**: Evaluate hundreds of tickets with progress tracking
- **Analytics Dashboard**: Score distributions, pass rates, common issues

## Quick Start

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/mmctech/IncidentReviews.git
cd IncidentReviews

# Install with pip
pip install -e .
```

### 2. Run the Application

```bash
streamlit run src/tqrs/ui/app.py
```

### 3. Use the Web Interface

1. Open http://localhost:8501 in your browser
2. Upload a ServiceNow JSON export (or click "Load Sample Data")
3. Select an evaluation template
4. Enter your OpenAI API key
5. Click "Start Evaluation"
6. View results and download reports

## Requirements

- Python 3.11+
- OpenAI API key (or Enterprise endpoint)

## Installation

### From Source

```bash
git clone https://github.com/mmctech/IncidentReviews.git
cd IncidentReviews
pip install -e .
```

### Dependencies

Core dependencies are installed automatically:
- `openai` - LLM API client
- `streamlit` - Web interface
- `pydantic` - Data validation
- `jinja2` - HTML report templates
- `plotly` - Charts and visualizations

## Configuration

### OpenAI API Key

Enter your API key in the web interface sidebar, or set it via environment variable:

```bash
export OPENAI_API_KEY=your-api-key-here
```

### Enterprise OpenAI / Azure OpenAI

For Enterprise endpoints, expand "Enterprise Settings" in the sidebar and enter your custom API Base URL:

```
https://your-endpoint.openai.azure.com/
```

### Environment Variables

Create a `.env` file (see `envexample`):

```bash
# Required
OPENAI_API_KEY=your-api-key-here

# Optional - Enterprise endpoint
OPENAI_BASE_URL=https://your-enterprise-endpoint.openai.azure.com/

# Optional - Model settings
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.1
```

## Usage Guide

### Uploading Tickets

The system accepts ServiceNow JSON exports with this structure:

```json
{
  "records": [
    {
      "number": "INC8924218",
      "category": "software",
      "subcategory": "reset_restart",
      "short_description": "MMC-NCL Bangalore-VDI-error message",
      "description": "Full ticket description...",
      "close_notes": "Resolution notes...",
      ...
    }
  ]
}
```

### Evaluation Templates

| Template | Focus | Key Criteria |
|----------|-------|--------------|
| **Incident Logging** | Documentation quality | Category, description, short description format |
| **Incident Handling** | Resolution process | Troubleshooting, routing, resolution notes |
| **Customer Service** | Interaction quality | Greeting, empathy, follow-through |

### Scoring

- **Maximum Score**: 70 points
- **Pass Threshold**: 63 points (90%)
- **Performance Bands**:
  - BLUE: 95%+ (Exceptional)
  - GREEN: 90-94% (Pass)
  - YELLOW: 75-89% (Needs Improvement)
  - RED: 50-74% (Below Standard)
  - PURPLE: <50% (Critical)

### Deductions

- **Validation**: -15 points if not properly documented
- **Critical Process**: -35 points for process violations
- **Auto-Fail**: Password process violations result in automatic failure

### Exporting Results

From the Export tab:
- **JSON**: Complete evaluation data
- **CSV**: Summary spreadsheet
- **HTML Batch Report**: Professional summary with charts
- **HTML Individual Reports**: Detailed per-ticket reports

## Project Structure

```
src/tqrs/
├── models/          # Pydantic data models
├── parser/          # ServiceNow JSON parser
├── rules/           # Deterministic rule evaluators
├── llm/             # OpenAI LLM integration
├── scoring/         # Score calculation engine
├── reports/         # HTML report generation
└── ui/              # Streamlit web interface
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
ruff check src/
ruff format src/
```

## License

MIT License

## Support

For issues and feature requests, please use the GitHub issue tracker.
