# ServiceNow Export Guide for TQRS

This guide explains how to export incident data from ServiceNow for use with the Ticket Quality Review System (TQRS).

## Quick Start

1. Navigate to **Incident** > **All** in ServiceNow
2. Apply the filters below based on your evaluation needs
3. Export as **JSON**
4. Upload the JSON file to TQRS

---

## Required Fields

Ensure your ServiceNow list view includes these fields before exporting:

### Core Fields (Required)
| Field | ServiceNow Column | Purpose |
|-------|-------------------|---------|
| Number | `number` | Ticket identifier |
| Sys ID | `sys_id` | Unique record ID |
| Short Description | `short_description` | 4-part format validation |
| Description | `description` | Issue documentation quality |
| Close Notes | `close_notes` | Resolution documentation |
| Close Code | `close_code` | Resolution classification |

### Date Fields (Required)
| Field | ServiceNow Column | Purpose |
|-------|-------------------|---------|
| Opened | `opened_at` | Ticket creation time |
| Resolved | `resolved_at` | Resolution timestamp |
| Closed | `closed_at` | Closure timestamp |

### Classification Fields (Required)
| Field | ServiceNow Column | Purpose |
|-------|-------------------|---------|
| Category | `category` | Category validation |
| Subcategory | `subcategory` | Subcategory validation |
| Contact Type | `contact_type` | Determines validation requirements |
| Priority | `priority` | VIP handling validation |
| State | `state` | Ticket status |

### Line of Business Flags (Required)
| Field | ServiceNow Column | Purpose |
|-------|-------------------|---------|
| Is Marsh | `u_is_marsh` | LoB identification |
| Is GC | `u_is_gc` | LoB identification |
| Is Mercer | `u_is_mercer` | LoB identification |
| Is Oliver Wyman | `u_is_oliver_wyman` | LoB identification |

### Optional but Recommended
| Field | ServiceNow Column | Purpose |
|-------|-------------------|---------|
| Business Service | `business_service` | Service selection scoring |
| Configuration Item | `cmdb_ci` | CI selection scoring |
| Assigned To | `assigned_to` | Agent identification |
| Assignment Group | `assignment_group` | Team filtering |
| Reassignment Count | `reassignment_count` | Handling metrics |
| Reopen Count | `reopen_count` | Quality metrics |

---

## Recommended Filters by Template

### Incident Logging Template
*Evaluates: Short description format, category selection, initial documentation*

```
State = Closed
Closed >= Last 30 days
Contact Type != Self-Service (optional)
```

**ServiceNow Encoded Query:**
```
state=6^closed_atONLast 30 days@javascript:gs.daysAgoStart(30)@javascript:gs.daysAgoEnd(0)
```

### Incident Handling Template
*Evaluates: Troubleshooting documentation, resolution quality, process adherence*

```
State = Closed
Closed >= Last 30 days
Close Code != Cancelled
Close Notes is not empty
```

**ServiceNow Encoded Query:**
```
state=6^closed_atONLast 30 days@javascript:gs.daysAgoStart(30)@javascript:gs.daysAgoEnd(0)^close_code!=cancelled^close_notesISNOTEMPTY
```

### Customer Service Template
*Evaluates: Communication quality, professionalism, customer interaction*

```
State = Closed
Closed >= Last 30 days
Contact Type = Phone OR Chat
Close Notes is not empty
```

**ServiceNow Encoded Query:**
```
state=6^closed_atONLast 30 days@javascript:gs.daysAgoStart(30)@javascript:gs.daysAgoEnd(0)^contact_typeINphone,chat^close_notesISNOTEMPTY
```

---

## Filter by Team or Agent

### By Assignment Group
```
Assignment Group = [Your Team Name]
State = Closed
Closed >= Last 30 days
```

### By Specific Agent
```
Assigned To = [Agent Name]
State = Closed
Closed >= Last 30 days
```

---

## Special Considerations

### Validation-Required Tickets
For evaluating caller validation compliance, filter for phone contacts:

```
Contact Type = Phone
State = Closed
Closed >= Last 30 days
```

The system checks for validation documentation (OKTA Push, Employee ID, etc.) in the description and close notes.

### Critical Process Tickets
To focus on password reset and security-sensitive tickets:

```
Category = Inquiry/Help
Subcategory = Password Reset
State = Closed
Closed >= Last 30 days
```

Or search short description:
```
Short Description CONTAINS "password"
State = Closed
```

### VIP Tickets
To evaluate VIP handling compliance:

```
Priority = 1 - Critical OR 2 - High
Short Description CONTAINS "VIP"
State = Closed
```

---

## Export Procedure

### Step 1: Configure List View
1. Go to **Incident** > **All**
2. Right-click the column header
3. Select **Configure** > **List Layout**
4. Add all required fields from the tables above
5. Save the view

### Step 2: Apply Filters
1. Use the filter builder or paste the encoded query
2. Verify the result count is manageable (recommend < 500 tickets per batch)
3. Review a few records to confirm data quality

### Step 3: Export to JSON
1. Right-click the column header
2. Select **Export** > **JSON**
3. Choose **All records** or **This page** as needed
4. Save the file

### Step 4: Upload to TQRS
1. Open TQRS Streamlit application
2. Navigate to the Upload section
3. Select your JSON file
4. Choose the appropriate evaluation template
5. Run the evaluation

---

## Recommended Batch Sizes

| Scenario | Recommended Size | Reason |
|----------|------------------|--------|
| Initial testing | 10-20 tickets | Verify configuration |
| Regular reviews | 50-100 tickets | Manageable review session |
| Team audits | 100-200 tickets | Comprehensive coverage |
| Large batches | 200-500 tickets | Use Azure OpenAI for reliability |

**Note:** Large batches (500+ tickets) may encounter API rate limits with standard OpenAI. Use Azure OpenAI endpoint for enterprise-scale evaluations.

---

## Troubleshooting

### Missing Fields in Export
If fields are missing from your JSON export:
1. Verify the field is in your list view
2. Check field-level security permissions
3. Ensure the field has data (empty fields may be omitted)

### Empty Close Notes
Tickets with empty close notes will score poorly on resolution documentation. Filter these out or ensure agents complete close notes before closing tickets.

### Contact Type Variations
The system recognizes these contact types:
- `phone` - Requires validation documentation
- `chat` - Requires validation documentation
- `email` - No validation required
- `self-service` - No validation required
- `walk-in` - Treated as phone (validation required)

### Date Range Recommendations
| Purpose | Date Range |
|---------|------------|
| Weekly coaching | Last 7 days |
| Monthly reviews | Last 30 days |
| Quarterly audits | Last 90 days |
| Trend analysis | Custom range |

---

## Sample JSON Structure

TQRS expects JSON in this format (ServiceNow default export):

```json
{
  "records": [
    {
      "number": "INC0012345",
      "sys_id": "abc123...",
      "short_description": "MARSH - Sydney - VDI - Unable to connect",
      "description": "User called reporting...",
      "close_notes": "Resolved by...",
      "category": "Software",
      "subcategory": "Operating System",
      "contact_type": "phone",
      "priority": "3",
      "state": "6",
      "opened_at": "2024-01-15 09:30:00",
      "closed_at": "2024-01-15 10:45:00",
      "u_is_marsh": "true",
      ...
    }
  ]
}
```

---

## Need Help?

- **Workflow Charts**: See `docs/workflow_charts.html` for visual evaluation flow
- **Scoring Rubrics**: Check `src/tqrs/scoring/rubrics/` for detailed criteria
- **Issues**: Report problems at the project repository
