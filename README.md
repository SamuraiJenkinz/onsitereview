# TQRS - Ticket Quality Review System

AI-powered ServiceNow ticket quality review system that automates the evaluation of incident tickets using a hybrid rules + LLM approach.

## Features

- **Automated Scoring**: 70-point evaluation across multiple criteria
- **Two Templates**: Incident Logging and Incident Handling
- **AI-Powered Analysis**: OpenAI GPT-4o for nuanced quality assessment
- **Professional Reports**: HTML reports with score gauges and coaching recommendations
- **Batch Processing**: Evaluate hundreds of tickets with progress tracking
- **Analytics Dashboard**: Score distributions, pass rates, common issues

## Quick Start

### 1. Install Dependencies

```powershell
# Clone the repository
git clone https://github.com/mmctech/IncidentReviews.git
cd IncidentReviews

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Run the Application

```powershell
streamlit run src/tqrs/ui/app.py
```

### 3. Use the Web Interface

1. Open http://localhost:8501 in your browser
2. Upload a ServiceNow JSON export (or click "Load Sample Data")
3. Select an evaluation template
4. Enter your OpenAI API key (or configure Azure OpenAI in sidebar)
5. Click "Start Evaluation"
6. View results and download reports

## Requirements

- Python 3.11+
- OpenAI API key or Azure OpenAI endpoint

## Installation

### Development (Local)

```powershell
git clone https://github.com/mmctech/IncidentReviews.git
cd IncidentReviews
python -m venv venv
venv\Scripts\activate
pip install -e .
streamlit run src/tqrs/ui/app.py
```

### Windows Server Deployment

Deploy as a Windows scheduled task that auto-starts on boot:

```powershell
# Clone to your preferred location (e.g., D:\incidentreviews)
D:
git clone https://github.com/mmctech/IncidentReviews.git incidentreviews
cd incidentreviews

# Create virtual environment
python -m venv venv
venv\Scripts\pip install -e .

# Install as Windows service (run as Administrator)
.\setup_service.ps1 -Port 8502
```

**Service Management:**

```powershell
.\manage_service.ps1 -Action status    # Check service status
.\manage_service.ps1 -Action stop      # Stop service
.\manage_service.ps1 -Action start     # Start service
.\manage_service.ps1 -Action restart   # Restart service
.\manage_service.ps1 -Action remove    # Uninstall service
```

**Custom Installation Path:**

```powershell
.\setup_service.ps1 -AppPath "E:\myapps\tqrs" -Port 8080
```

### Dependencies

Core dependencies are installed automatically:
- `openai` - LLM API client
- `streamlit` - Web interface
- `pydantic` - Data validation
- `jinja2` - HTML report templates
- `plotly` - Charts and visualizations

## Configuration

All API configuration is done through the web interface sidebar.

### OpenAI

1. Enter your API key in the sidebar
2. Click "Start Evaluation"

### Azure OpenAI

1. Expand "Enterprise Settings" in the sidebar
2. Check "Use Azure OpenAI"
3. Enter your Azure endpoint, deployment name, and API version
4. Click "Start Evaluation"

### Enterprise OpenAI

1. Expand "Enterprise Settings" in the sidebar
2. Enter your custom API Base URL
3. Click "Start Evaluation"

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

> **Note:** Customer Service template has been disabled. Its criteria (greeting, closing message, interaction quality) require phone/chat transcript data from systems like Five9, which is not captured in ServiceNow incident records.

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
