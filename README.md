# TQRS - Ticket Quality Review System

AI-powered ServiceNow ticket quality review system that automates the evaluation of onsite support incident tickets using a hybrid rules + LLM approach.

## Features

- **Automated Scoring**: 90-point evaluation across 8 criteria (Onsite Support Review)
- **AI-Powered Analysis**: OpenAI GPT-4o for nuanced quality assessment
- **Professional Reports**: HTML reports with score gauges and coaching recommendations
- **Path to Passing**: Actionable recommendations for failing tickets
- **Batch Processing**: Evaluate hundreds of tickets with progress tracking
- **Analytics Dashboard**: Score distributions, pass rates, common issues

## Quick Start

### 1. Install Dependencies

```powershell
# Clone the repository
git clone https://github.com/SamuraiJenkinz/onsitereview.git
cd onsitereview

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Run the Application

```powershell
streamlit run src/onsitereview/ui/app.py
```

### 3. Use the Web Interface

1. Open http://localhost:8501 in your browser
2. Upload a ServiceNow JSON export (or click "Load Sample Data")
3. Enter your OpenAI API key (or configure Azure OpenAI in sidebar)
4. Click "Start Evaluation"
5. View results and download reports

## Requirements

- Python 3.11+
- OpenAI API key or Azure OpenAI endpoint

## Installation

### Development (Local)

```powershell
git clone https://github.com/SamuraiJenkinz/onsitereview.git
cd onsitereview
python -m venv venv
venv\Scripts\activate
pip install -e .
streamlit run src/onsitereview/ui/app.py
```

### Windows Server Deployment

Deploy as a Windows scheduled task that auto-starts on boot:

```powershell
# Clone to your preferred location (e.g., D:\onsitereview)
D:
git clone https://github.com/SamuraiJenkinz/onsitereview.git
cd onsitereview

# Create virtual environment
python -m venv venv
venv\Scripts\pip install -e .

# Configure Azure OpenAI credentials (run as Administrator)
.\configure_credentials.ps1 -Endpoint "https://your-resource.openai.azure.com/" -ApiKey "your-api-key" -Deployment "gpt-4o"

# Install as Windows service (run as Administrator)
.\setup_service.ps1 -Port 8502
```

**Server-Side Credential Configuration:**

Configure Azure OpenAI credentials as system environment variables. This hides credentials from end users - they'll see "Using server-configured credentials" instead of API key inputs.

```powershell
# Set credentials (requires Administrator)
.\configure_credentials.ps1 -Endpoint "https://your-resource.openai.azure.com/" -ApiKey "your-api-key" -Deployment "gpt-4o"

# Check current configuration
.\configure_credentials.ps1 -Status

# Remove credentials
.\configure_credentials.ps1 -Clear
```

Environment variables used:
- `TQRS_AZURE_OPENAI_ENDPOINT` - Azure OpenAI resource URL
- `TQRS_AZURE_OPENAI_API_KEY` - API key
- `TQRS_AZURE_OPENAI_DEPLOYMENT` - Model deployment name
- `TQRS_AZURE_OPENAI_API_VERSION` - API version (optional)

**Admin Override:** Access `http://server:port/?admin=true` to temporarily override server credentials for testing.

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

### Server Deployment (Recommended)

For Windows Server deployments, configure credentials via environment variables. This hides credentials from end users:

```powershell
.\configure_credentials.ps1 -Endpoint "https://..." -ApiKey "..." -Deployment "gpt-4o"
```

See [Windows Server Deployment](#windows-server-deployment) for details.

### Manual Configuration (Development)

For local development, configure API settings through the web interface sidebar.

**OpenAI:**
1. Select "OpenAI" provider
2. Enter your API key in the sidebar
3. Click "Start Evaluation"

**Azure OpenAI:**
1. Select "Azure OpenAI" provider
2. Enter your Azure endpoint, deployment name, and API key
3. Click "Start Evaluation"

**Enterprise OpenAI:**
1. Select "OpenAI" provider
2. Expand "Enterprise Settings"
3. Enter your custom API Base URL
4. Click "Start Evaluation"

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

### Scoring

**Onsite Support Review** - Single unified template, 90 points across 8 criteria:

| # | Criterion | Points | Method |
|---|-----------|--------|--------|
| 1 | Category | 5 | LLM |
| 2 | Subcategory | 5 | LLM |
| 3 | Service | 5 | LLM |
| 4 | Configuration Item | 10 | LLM |
| 5 | Opened For | 10 | Rules |
| 6 | Incident Notes | 20 | LLM |
| 7 | Incident Handling | 15 | LLM |
| 8 | Resolution Notes | 20 | LLM |

- **Maximum Score**: 90 points
- **Pass Threshold**: 81 points (90%)
- **Performance Bands**:
  - BLUE: 95%+ (Exceptional)
  - GREEN: 90-94% (Pass)
  - YELLOW: 75-89% (Needs Improvement)
  - RED: 50-74% (Below Standard)
  - PURPLE: <50% (Critical)

### Exporting Results

From the Export tab:
- **JSON**: Complete evaluation data
- **CSV**: Summary spreadsheet
- **HTML Batch Report**: Professional summary with charts
- **HTML Individual Reports**: Detailed per-ticket reports

## Project Structure

```
src/onsitereview/
├── models/          # Pydantic data models
├── parser/          # ServiceNow JSON parser
├── rules/           # Deterministic rule evaluators (Opened For check)
├── llm/             # OpenAI LLM integration (7 criteria)
├── scoring/         # Score calculation engine (90 points)
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

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Complete guide for using TQRS
- [ServiceNow Export Guide](docs/servicenow_export_guide.md) - How to export tickets from ServiceNow
- [Workflow Charts](docs/workflow_charts.html) - Visual evaluation process diagrams

## Support

For issues and feature requests, please use the GitHub issue tracker.
