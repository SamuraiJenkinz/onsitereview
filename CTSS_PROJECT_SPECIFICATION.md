# CTSS Ticket Quality Review - AI-Powered Automation System
## Complete Technical Specification for Claude Code

**Project:** Automated ServiceNow Ticket Quality Review System  
**Client:** Global Service Desk Team  
**Date:** December 26, 2025  
**Version:** 1.0  

---

## EXECUTIVE SUMMARY

### Project Goal
Replace manual Excel-based ticket quality review process with AI-powered automation that reduces review time from 15-25 minutes per ticket to <2 minutes while improving consistency and accuracy.

### Scope
Build a Python application that:
1. Parses ServiceNow incident JSON exports
2. Evaluates tickets against three quality templates (70-point scoring system)
3. Generates professional HTML reports with detailed scoring and coaching recommendations

### Success Criteria
- **Accuracy:** 88-94% agreement with human reviewers
- **Time Savings:** 85-95% reduction in review time
- **Consistency:** 100% (no human fatigue/bias)
- **Scalability:** Process 100+ tickets in batch mode

---

## SYSTEM ARCHITECTURE

### High-Level Flow
```
ServiceNow JSON Export
        ↓
┌─────────────────────────┐
│   JSON Parser           │
│   - Validate structure  │
│   - Extract fields      │
│   - Build context       │
└─────────────────────────┘
        ↓
┌─────────────────────────┐
│   Ticket Evaluator      │
│   ┌──────────┬─────────┐│
│   │ Rules    │ LLM     ││
│   │ Engine   │ Agent   ││
│   │ (40%)    │ (60%)   ││
│   └──────────┴─────────┘│
└─────────────────────────┘
        ↓
┌─────────────────────────┐
│   Scoring Engine        │
│   - Calculate points    │
│   - Apply deductions    │
│   - Assign band         │
└─────────────────────────┘
        ↓
┌─────────────────────────┐
│   Report Generator      │
│   - HTML output         │
│   - Coaching insights   │
│   - Visualizations      │
└─────────────────────────┘
```

### Technology Stack
```python
Core:
- Python 3.12+
- JSON parsing (native json module)

AI/LLM:
- Anthropic Claude Sonnet 4 API
- Structured output with JSON schema

Rules Engine:
- Custom Python logic
- Regex pattern matching
- LanguageTool API (spelling/grammar)

Report Generation:
- Jinja2 templates
- Tailwind CSS (CDN)
- Plotly.js (visualizations)

Deployment:
- Desktop Python script (Phase 1)
- Optional: Flask/FastAPI web app (Phase 2)
```

---

## DATA STRUCTURE

### ServiceNow JSON Format

**Input File Structure:**
```json
{
  "records": [
    {
      "number": "INC8924218",
      "sys_id": "unique_identifier",
      "sys_created_on": "2025-12-10 04:26:41",
      "sys_updated_on": "2025-12-15 05:00:35",
      
      "category": "software",
      "subcategory": "reset_restart",
      "cmdb_ci": "cd0fa01c472e8910af5bebbd436d4319",
      "short_description": "MMC-NCL Bangalore-VDI-error message",
      "description": "Full description with validation, issue details, troubleshooting",
      
      "priority": "5",
      "impact": "3",
      "urgency": "3",
      "state": "7",
      "incident_state": "7",
      
      "assignment_group": "24e9e0ad1bd541502f537732dd4bcb70",
      "assigned_to": "57e5835c33336a503c4f61a9ed5c7b5d",
      
      "close_code": "Solved (Permanently)",
      "close_notes": "Resolution steps and confirmation",
      
      "work_notes": "",
      "work_notes_list": "",
      "comments": "",
      "comments_and_work_notes": "",
      
      "caller_id": "ce75dce63b0c625474a9dfa9e5e45a99",
      "contact_type": "phone",
      "location": "4bd4d1348738459067dfb997cebb3506",
      
      "parent_incident": "",
      "parent": "",
      "child_incidents": "0",
      "origin_id": "",
      "origin_table": "",
      
      "u_mercer": "false",
      "u_marsh": "false",
      "u_guy_carpenter": "false",
      "u_mmc_corporate": "false",
      "u_oliver_wyman_group": "false",
      
      "opened_at": "2025-12-10 04:26:00",
      "resolved_at": "2025-12-10 04:41:00",
      "closed_at": "2025-12-15 05:00:00",
      
      "business_duration": "1970-01-01 00:00:00",
      "calendar_duration": "1970-01-01 00:15:00"
    }
  ]
}
```

### Field Mapping Reference

| Evaluation Need | ServiceNow Field | Type | Notes |
|----------------|------------------|------|-------|
| Incident Number | `number` | String | e.g., "INC8924218" |
| Category | `category` | String | e.g., "software", "inquiry", "hardware" |
| Subcategory | `subcategory` | String | e.g., "password reset", "reset_restart" |
| Configuration Item | `cmdb_ci` | String (sys_id) | May be sys_id or display value |
| Short Description | `short_description` | String | Must be 4-part format |
| Description | `description` | Text | Contains validation, issue, troubleshooting |
| Priority | `priority` | String | "1" to "5" (lower = higher priority) |
| State | `state` | String | "7" = Closed, "6" = Resolved |
| Close Code | `close_code` | String | e.g., "Solved (Permanently)" |
| Close Notes | `close_notes` | Text | Resolution documentation |
| Contact Type | `contact_type` | String | "phone", "chat", "email" |
| Caller ID | `caller_id` | String (sys_id) | Reference to user |
| Assignment Group | `assignment_group` | String (sys_id) | Support team |
| Parent Incident | `parent_incident` or `parent` | String | For interaction linking |
| Line of Business | `u_mercer`, `u_marsh`, etc. | Boolean | "true"/"false" strings |

---

## SCORING RUBRICS

### Template 1: Incident Logging (70 points max)

#### Scoring Breakdown

| Criterion | Max Points | Evaluation Method | Scoring Options |
|-----------|-----------|-------------------|-----------------|
| **Correct Category** | 10 | Rule-based | 10: Correct<br>5: Better available<br>0: Incorrect |
| **Correct Subcategory** | 10 | Rule-based | 10: Correct<br>5: Better available<br>0: Incorrect |
| **Correct Service** | 10 | Rule-based | 10: Correct<br>5: Better available<br>0: Incorrect |
| **Correct Configuration Item** | 10 | Rule-based | 10: Correct<br>5: Better available<br>0: Incorrect |
| **Accurate Short Description** | 8 | Hybrid | 8: All 4 parts correct<br>6: 1 item wrong<br>4: 2 items wrong<br>2: 3 items wrong<br>0: 4 items wrong |
| **Accurate Description** | 20 | LLM | 20: Complete<br>15: 1 item missing<br>10: 2 items missing<br>5: 3 items missing<br>0: 4+ items missing |
| **Spelling/Grammar** | 2 | Rule-based | 2: Perfect<br>1: 1-4 errors<br>0: 5+ errors |
| **Validation** | PASS/-15/FAIL | Special | PASS: Documented correctly<br>-15: Done but not documented<br>N/A: OKTA validated<br>FAIL: Not validated |
| **Critical Process** | PASS/-35/FAIL | Special | PASS: Followed<br>-35: Failed (non-password)<br>FAIL: Password process failed<br>N/A: Not applicable |

#### Short Description Format (4-Part)
```
[LoB] - [Location] - [Application/Device] - [Brief Description]

Examples:
✓ "Mercer - Boston - Domain Account - Password Reset"
✓ "GC - London - VDI - Cannot Log In"
✓ "MMC - Bangalore - VDI - error message"

Validation Rules:
- LoB: Line of Business (Mercer, Marsh, GC, MMC, OW)
- Location: City name ONLY (not building)
- Application: The ACTUAL affected system (not initial report)
- Description: Max 8 words, must be specific
```

#### Description Requirements
Must include:
1. **Validation documentation** (using template format)
2. **Issue statement** (elaborates on short description)
3. **Working location** (office vs remote)
4. **Contact number**
5. **For password resets:** Application/account username
6. **All relevant colleague information**

#### Validation Template Patterns
```
Phone Validation:
"Validated by: Okta Push MFA & Full Name"
"Contact Number: XXXXXXXXXX"
"Working remotely: Y/N"
"Issue/Request: [description]"

Chat Validation (Guest):
"Validated by: Employee ID, full name and location"
"Caller/chatter is affected colleague: Y"

Chat Validation (OKTA):
"Okta Push Validation: Colleague Validated"
```

---

### Template 2: Incident Handling (70 points max)

#### Scoring Breakdown

| Criterion | Max Points | Evaluation Method | Scoring Options |
|-----------|-----------|-------------------|-----------------|
| **Correct Priority** | 5 | Rule-based | 5: Correct<br>0: Incorrect |
| **Troubleshooting** | 20 | LLM | 20: Sufficient & documented<br>15: Done but poorly documented<br>10: Some troubleshooting<br>5: Limited<br>0: None<br>N/A: Not required |
| **Interaction vs Incident** | 5 | Hybrid | 5: Correct usage<br>0: Incorrect (no interaction attached or should be interaction only) |
| **Incident Routing/Resolving** | 20 | LLM | 20: Routed/resolved correctly<br>0: FCR missed or incorrect routing |
| **Resolution Code** | 5 | Rule-based | 5: Correct<br>0: Incorrect<br>N/A: Routed/not resolved |
| **Resolution Notes** | 15 | LLM | 15: All 3 items present<br>10: 1 item missing<br>5: 2 items missing<br>0: Incomplete or no confirmation<br>N/A: Not resolved |
| **Validation** | PASS/-15/FAIL | Special | Same as Incident Logging |
| **Critical Process** | PASS/-35/FAIL | Special | Same as Incident Logging |

#### Priority Rules
```
VIP tickets: U1/I3 (Priority 1 or 2)
OWG tickets: U2/I2 (Priority 2 or 3)
Standard: Based on impact/urgency matrix
```

#### Resolution Notes Requirements
Must include ALL THREE:
1. **What was done** to resolve the issue
2. **Confirmation** issue is resolved
3. **Confirmation** colleague agreed to close ticket

Example:
```
Good: "Password reset via AD. User confirmed able to log in. Colleague 
      agreed ticket can be closed."

Bad:  "Password reset." (missing confirmation)
```

---

### Template 3: Customer Service (70 points max)

#### Scoring Breakdown

| Criterion | Max Points | Evaluation Method | Scoring Options |
|-----------|-----------|-------------------|-----------------|
| **Greeting** | 5 | LLM | 5: Professional greeting<br>0: No greeting |
| **Offer Work Around** | 10 | LLM | 10: Offered when applicable<br>0: Not offered<br>N/A: Not applicable |
| **Necessary Troubleshooting** | 10 | LLM | 10: All necessary, no unnecessary<br>0: Unnecessary steps performed<br>N/A: Not required |
| **Self-Resolve Training** | 10 | LLM | 10: Offered training<br>0: Did not offer<br>N/A: Not applicable |
| **Resolution Follow-through** | 10 | LLM | 10: Followed through<br>0: Did not follow through |
| **Closing Message** | 5 | LLM | 5: Professional closing<br>0: No closing |
| **General Customer Service** | 20 | LLM | 20: Excellent (friendly, quick, effective)<br>15: Good (polite, effective)<br>10: Adequate (works but minimal communication)<br>5: Poor (unfriendly or ineffective)<br>0: Unprofessional/rude |
| **Validation** | PASS/-15/FAIL | Special | Same as above |
| **Critical Process** | PASS/-35/FAIL | Special | Same as above |

**Note:** Customer Service evaluation requires call recordings or chat transcripts. For phone incidents, evaluation is based on documentation in the ticket unless Five9 call recordings are available.

---

### Scoring Calculations

#### Base Score Calculation
```python
base_score = sum(criterion_scores)  # 0-70 points
```

#### Deductions
```python
# Validation deduction
if validation_status == "FAIL" or validation_status == -15:
    base_score -= 15

# Critical Process deduction  
if critical_process == "FAIL":
    base_score = 0  # Automatic fail for password process
elif critical_process == -35:
    base_score -= 35

# Ensure minimum score
final_score = max(0, base_score)
```

#### Performance Bands
```python
percentage = (final_score / 70) * 100

if percentage >= 95.0:
    band = "BLUE"    # Exceeding target
    status = "PASS"
elif percentage >= 90.0:
    band = "GREEN"   # On track
    status = "PASS"
elif percentage >= 75.0:
    band = "YELLOW"  # Some improvement required
    status = "FAIL"
elif percentage >= 50.0:
    band = "RED"     # Major improvement required
    status = "FAIL"
else:
    band = "PURPLE"  # Urgent improvement required
    status = "FAIL"
```

**Pass Threshold:** 63/70 points (90%)

---

## CRITICAL PROCESSES

### List of Critical Processes
1. **Password Resets** (FAIL = automatic 0 score)
2. **Failed Validation**
3. **Lost/Stolen devices**
4. **MIM (Mobile Iron Management)**
5. **VIP tickets**
6. **OWG (Operating Work Group)**
7. **Virus incidents**
8. **Callback procedures**
9. **Escalations & Failed Escalations**
10. **ICAT**
11. **Crisis Management**
12. **Data Privacy/Security Incidents**

### Detection Logic
```python
def detect_critical_process(incident):
    description = incident.get('description', '').lower()
    category = incident.get('category', '').lower()
    subcategory = incident.get('subcategory', '').lower()
    
    critical_indicators = {
        'password': ['password reset', 'password', 'pwd reset'],
        'vip': ['vip', 'priority 1', 'u1'],
        'owg': ['owg', 'operating work group'],
        'lost_stolen': ['lost', 'stolen', 'missing device'],
        'virus': ['virus', 'malware', 'infected'],
        'security': ['security incident', 'data breach', 'privacy']
    }
    
    # Return detected critical process type
    # Return 'none' if no critical process
```

---

## LINE OF BUSINESS (LOB) DETECTION

### Field-Based Detection
```python
def detect_lob(incident):
    """
    Detect Line of Business from boolean flags or description
    """
    if incident.get('u_mercer') == 'true':
        return 'Mercer'
    elif incident.get('u_marsh') == 'true':
        return 'Marsh'
    elif incident.get('u_guy_carpenter') == 'true':
        return 'GC'
    elif incident.get('u_mmc_corporate') == 'true':
        return 'MMC'
    elif incident.get('u_oliver_wyman_group') == 'true':
        return 'OW'
    else:
        # Fallback: parse from short_description
        short_desc = incident.get('short_description', '')
        # Extract first word before hyphen
        return extract_lob_from_text(short_desc)
```

### Valid LOB Values
- **Mercer** - Mercer LLC
- **Marsh** - Marsh & McLennan
- **GC** / **GuyCarp** - Guy Carpenter
- **MMC** - MMC Corporate
- **OW** - Oliver Wyman

---

## LLM EVALUATION PROMPTS

### Prompt Template Structure

```python
EVALUATION_PROMPT_TEMPLATE = """
You are an expert ServiceNow ticket quality reviewer for a global service desk.

TICKET TO EVALUATE:
Number: {number}
Category: {category}
Subcategory: {subcategory}
Short Description: {short_description}
Description: {description}
Close Code: {close_code}
Close Notes: {close_notes}

EVALUATION CRITERIA:
{criteria_specific_instructions}

SCORING RUBRIC:
{scoring_rubric}

INSTRUCTIONS:
1. Evaluate the ticket against each criterion
2. Provide a score for each criterion
3. Provide evidence/reasoning for each score
4. Suggest specific coaching improvements

OUTPUT FORMAT (JSON):
{{
  "evaluations": [
    {{
      "criterion": "criterion_name",
      "score": numeric_score,
      "evidence": "quote or reference from ticket",
      "reasoning": "why this score was assigned",
      "coaching": "specific improvement recommendation"
    }}
  ],
  "overall_assessment": "brief summary"
}}
"""
```

### Example: Troubleshooting Evaluation

```python
TROUBLESHOOTING_PROMPT = """
Evaluate the TROUBLESHOOTING quality for this ticket.

TROUBLESHOOTING DOCUMENTATION:
{description}
{close_notes}

CRITERIA:
- Were troubleshooting steps documented?
- Are steps relevant to the issue?
- Are steps clearly presented?
- Is there evidence of systematic approach?

SCORING:
20 points: Sufficient troubleshooting conducted & documented
15 points: Sufficient troubleshooting but not sufficiently documented
10 points: Some troubleshooting conducted and documented
5 points: Limited low-level troubleshooting
0 points: No troubleshooting or no documentation
N/A: No troubleshooting required (simple request)

Respond with JSON:
{{
  "score": 20,
  "steps_identified": ["step1", "step2"],
  "evidence": "quoted text showing troubleshooting",
  "reasoning": "why this score",
  "coaching": "specific improvement"
}}
"""
```

### Example: Customer Service Evaluation

```python
CUSTOMER_SERVICE_PROMPT = """
Evaluate GENERAL CUSTOMER SERVICE quality based on ticket documentation.

TICKET DOCUMENTATION:
{description}
{close_notes}

CRITERIA TO ASSESS:
- Friendliness and professionalism
- Responsiveness and efficiency
- Clear communication
- Eagerness to help
- Keeps colleague informed

SCORING:
20: Excellent - Friendly, polite, quick, effective, shows eagerness to help
15: Good - Polite, friendly, effective but not particularly quick
10: Adequate - Effective but minimal communication with colleague
5: Poor - Not friendly/helpful OR doesn't understand colleague needs
0: Unprofessional - Rude, unhelpful, does not assist colleague

Respond with JSON:
{{
  "score": 15,
  "positive_aspects": ["aspect1", "aspect2"],
  "areas_for_improvement": ["area1", "area2"],
  "evidence": "quoted examples",
  "reasoning": "explanation",
  "coaching": "specific recommendations"
}}
"""
```

---

## RULES ENGINE SPECIFICATIONS

### Short Description Parser

```python
def evaluate_short_description(short_desc, incident):
    """
    Validate 4-part format: [LoB] - [Location] - [Application] - [Brief Desc]
    
    Returns: {
        'score': 0-8,
        'parts_correct': 4,
        'errors': [],
        'evidence': {}
    }
    """
    parts = short_desc.split(' - ')
    
    if len(parts) != 4:
        return {'score': 0, 'errors': ['Not 4-part format']}
    
    lob, location, application, brief = parts
    errors = []
    
    # Validate LoB
    valid_lobs = ['Mercer', 'Marsh', 'GC', 'GuyCarp', 'MMC', 'OW']
    if lob not in valid_lobs:
        errors.append(f'Invalid LoB: {lob}')
    
    # Validate Location (city name, not building)
    if any(word in location.lower() for word in ['building', 'floor', 'room']):
        errors.append(f'Location should be city, not building: {location}')
    
    # Validate Brief Description (max 8 words, specific)
    brief_words = brief.split()
    if len(brief_words) > 8:
        errors.append(f'Brief description too long: {len(brief_words)} words')
    
    generic_phrases = ['not working', 'issue', 'problem', 'help']
    if brief.lower() in generic_phrases:
        errors.append(f'Brief description too vague: {brief}')
    
    # Calculate score
    items_correct = 4 - len(errors)
    score_map = {4: 8, 3: 6, 2: 4, 1: 2, 0: 0}
    score = score_map.get(items_correct, 0)
    
    return {
        'score': score,
        'parts_correct': items_correct,
        'errors': errors,
        'evidence': {'lob': lob, 'location': location, 'application': application}
    }
```

### Spelling/Grammar Checker

```python
import language_tool_python

def check_spelling_grammar(text):
    """
    Uses LanguageTool API to check spelling and grammar
    
    Returns: {
        'score': 0-2,
        'error_count': int,
        'errors': [list of errors]
    }
    """
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    
    error_count = len(matches)
    
    if error_count == 0:
        score = 2
    elif error_count <= 4:
        score = 1
    else:
        score = 0
    
    return {
        'score': score,
        'error_count': error_count,
        'errors': [str(match) for match in matches[:10]]  # Limit to 10
    }
```

### Category/Service Validation

```python
# Taxonomy validation (would need actual ServiceNow taxonomy)
VALID_CATEGORIES = {
    'software': ['reset_restart', 'performance', 'error message', 'access issue'],
    'hardware': ['printer', 'laptop', 'monitor', 'keyboard'],
    'inquiry': ['password reset', 'access request', 'how-to', 'other'],
    'network': ['connectivity', 'vpn', 'wireless']
}

def validate_category_subcategory(category, subcategory):
    """
    Validate category and subcategory match
    
    Returns: {
        'category_score': 0/5/10,
        'subcategory_score': 0/5/10,
        'reasoning': str
    }
    """
    if category not in VALID_CATEGORIES:
        return {'category_score': 0, 'reasoning': 'Invalid category'}
    
    if subcategory in VALID_CATEGORIES[category]:
        return {
            'category_score': 10,
            'subcategory_score': 10,
            'reasoning': 'Correct match'
        }
    else:
        return {
            'category_score': 5,
            'subcategory_score': 5,
            'reasoning': 'Better subcategory may be available'
        }
```

### Validation Detection

```python
def detect_validation(description, contact_type):
    """
    Detect if validation was documented properly
    
    Returns: 'PASS', -15, 'FAIL', or 'N/A'
    """
    # Patterns for proper validation
    validation_patterns = [
        r'Validated by:.*Okta Push',
        r'Employee ID.*full name.*location',
        r'Contact Number:',
        r'Working remotely:'
    ]
    
    # Check for OKTA validation (N/A case)
    if 'Okta Push Validation: Colleague Validated' in description:
        return 'N/A'
    
    # Count how many validation elements are present
    matches = sum(1 for pattern in validation_patterns 
                  if re.search(pattern, description, re.IGNORECASE))
    
    if contact_type == 'email':
        return 'N/A'  # Email doesn't require phone validation
    
    if matches >= 3:
        return 'PASS'
    elif matches >= 1:
        return -15  # Validated but not documented properly
    else:
        return 'FAIL'
```

---

## HTML REPORT TEMPLATE

### Report Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ticket Quality Review - {{ incident_number }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body class="bg-gray-50 p-8">
    
    <!-- Header -->
    <div class="max-w-6xl mx-auto bg-white rounded-lg shadow-lg p-8 mb-8">
        <div class="flex justify-between items-start">
            <div>
                <h1 class="text-3xl font-bold text-gray-900">Ticket Quality Review</h1>
                <p class="text-xl text-gray-600 mt-2">{{ incident_number }}</p>
            </div>
            <div class="text-right">
                <div class="text-5xl font-bold {{ band_color }}">{{ percentage }}%</div>
                <div class="text-lg font-semibold {{ band_color }} mt-2">{{ band }}</div>
                <div class="text-sm text-gray-600 mt-1">{{ final_score }}/70 points</div>
            </div>
        </div>
    </div>
    
    <!-- Executive Summary -->
    <div class="max-w-6xl mx-auto bg-white rounded-lg shadow-lg p-8 mb-8">
        <h2 class="text-2xl font-bold mb-4">Executive Summary</h2>
        
        <div class="grid grid-cols-3 gap-6 mb-6">
            <div class="bg-blue-50 p-4 rounded-lg">
                <div class="text-sm text-gray-600">Template</div>
                <div class="text-lg font-semibold">{{ template_name }}</div>
            </div>
            <div class="bg-green-50 p-4 rounded-lg">
                <div class="text-sm text-gray-600">Contact Type</div>
                <div class="text-lg font-semibold">{{ contact_type }}</div>
            </div>
            <div class="bg-purple-50 p-4 rounded-lg">
                <div class="text-sm text-gray-600">Analyst</div>
                <div class="text-lg font-semibold">{{ analyst_name }}</div>
            </div>
        </div>
        
        <!-- Performance Band Visual -->
        <div id="score-gauge"></div>
    </div>
    
    <!-- Detailed Scoring -->
    <div class="max-w-6xl mx-auto bg-white rounded-lg shadow-lg p-8 mb-8">
        <h2 class="text-2xl font-bold mb-6">Detailed Scoring</h2>
        
        {% for criterion in evaluations %}
        <div class="border-b border-gray-200 pb-6 mb-6 last:border-b-0">
            <div class="flex justify-between items-start mb-3">
                <h3 class="text-xl font-semibold">{{ criterion.name }}</h3>
                <span class="text-2xl font-bold {{ criterion.score_color }}">
                    {{ criterion.score }}/{{ criterion.max_points }}
                </span>
            </div>
            
            <div class="bg-gray-50 p-4 rounded-lg mb-3">
                <div class="text-sm font-semibold text-gray-700 mb-1">Evidence:</div>
                <div class="text-gray-800">{{ criterion.evidence }}</div>
            </div>
            
            <div class="text-gray-700 mb-3">
                <span class="font-semibold">Reasoning:</span> {{ criterion.reasoning }}
            </div>
            
            {% if criterion.coaching %}
            <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div class="text-sm font-semibold text-yellow-800 mb-1">💡 Coaching Recommendation:</div>
                <div class="text-yellow-900">{{ criterion.coaching }}</div>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <!-- Ticket Details -->
    <div class="max-w-6xl mx-auto bg-white rounded-lg shadow-lg p-8 mb-8">
        <h2 class="text-2xl font-bold mb-6">Ticket Details</h2>
        
        <div class="grid grid-cols-2 gap-6">
            <div>
                <div class="text-sm text-gray-600">Category</div>
                <div class="font-medium">{{ category }} > {{ subcategory }}</div>
            </div>
            <div>
                <div class="text-sm text-gray-600">Priority</div>
                <div class="font-medium">{{ priority }}</div>
            </div>
            <div class="col-span-2">
                <div class="text-sm text-gray-600 mb-2">Short Description</div>
                <div class="font-medium bg-gray-50 p-3 rounded">{{ short_description }}</div>
            </div>
            <div class="col-span-2">
                <div class="text-sm text-gray-600 mb-2">Description</div>
                <div class="bg-gray-50 p-4 rounded whitespace-pre-wrap text-sm">{{ description }}</div>
            </div>
        </div>
    </div>
    
    <!-- Overall Coaching Summary -->
    <div class="max-w-6xl mx-auto bg-white rounded-lg shadow-lg p-8">
        <h2 class="text-2xl font-bold mb-6">Coaching Summary</h2>
        
        <div class="space-y-4">
            <div class="bg-green-50 border-l-4 border-green-400 p-4">
                <div class="font-semibold text-green-800 mb-2">✓ Strengths</div>
                <ul class="list-disc list-inside text-green-900">
                    {% for strength in strengths %}
                    <li>{{ strength }}</li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="bg-red-50 border-l-4 border-red-400 p-4">
                <div class="font-semibold text-red-800 mb-2">⚠ Areas for Improvement</div>
                <ul class="list-disc list-inside text-red-900">
                    {% for improvement in improvements %}
                    <li>{{ improvement }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    
    <script>
    // Gauge chart for score visualization
    var data = [{
        type: "indicator",
        mode: "gauge+number+delta",
        value: {{ percentage }},
        title: { text: "Overall Score", font: { size: 24 } },
        delta: { reference: 90, increasing: { color: "green" } },
        gauge: {
            axis: { range: [null, 100], tickwidth: 1 },
            bar: { color: "{{ band_color_hex }}" },
            steps: [
                { range: [0, 50], color: "#e5e7eb" },
                { range: [50, 75], color: "#fecaca" },
                { range: [75, 90], color: "#fef3c7" },
                { range: [90, 95], color: "#d1fae5" },
                { range: [95, 100], color: "#bfdbfe" }
            ],
            threshold: {
                line: { color: "red", width: 4 },
                thickness: 0.75,
                value: 90
            }
        }
    }];
    
    var layout = {
        width: 600,
        height: 400,
        margin: { t: 25, r: 25, l: 25, b: 25 }
    };
    
    Plotly.newPlot('score-gauge', data, layout);
    </script>
</body>
</html>
```

---

## APPLICATION STRUCTURE

### File Organization
```
ctss_ticket_reviewer/
├── main.py                      # Entry point
├── config.py                    # Configuration settings
├── requirements.txt             # Dependencies
├── README.md                    # Documentation
│
├── parsers/
│   ├── __init__.py
│   ├── json_parser.py          # ServiceNow JSON parsing
│   └── field_extractor.py      # Extract/normalize fields
│
├── evaluators/
│   ├── __init__.py
│   ├── base_evaluator.py       # Base evaluation class
│   ├── rules_engine.py         # Rule-based evaluations
│   ├── llm_evaluator.py        # LLM-based evaluations
│   ├── incident_logging.py     # Template 1 evaluator
│   ├── incident_handling.py    # Template 2 evaluator
│   └── customer_service.py     # Template 3 evaluator
│
├── scoring/
│   ├── __init__.py
│   ├── calculator.py           # Score calculation
│   └── rubrics.py              # Scoring rubrics data
│
├── reporting/
│   ├── __init__.py
│   ├── html_generator.py       # HTML report generation
│   ├── templates/              # Jinja2 templates
│   │   ├── base.html
│   │   ├── incident_logging.html
│   │   ├── incident_handling.html
│   │   └── customer_service.html
│   └── assets/                 # CSS/JS assets
│
├── utils/
│   ├── __init__.py
│   ├── logging.py              # Logging configuration
│   └── validators.py           # Input validation
│
└── tests/
    ├── __init__.py
    ├── test_parser.py
    ├── test_evaluator.py
    └── fixtures/
        └── sample_tickets.json
```

### Main Application Flow

```python
# main.py

import sys
from pathlib import Path
from parsers.json_parser import ServiceNowParser
from evaluators.incident_logging import IncidentLoggingEvaluator
from scoring.calculator import ScoreCalculator
from reporting.html_generator import HTMLReportGenerator

def main():
    """
    Main application entry point
    """
    # 1. Parse command-line arguments
    if len(sys.argv) < 3:
        print("Usage: python main.py <input.json> <template>")
        print("Templates: incident_logging, incident_handling, customer_service")
        sys.exit(1)
    
    input_file = sys.argv[1]
    template = sys.argv[2]
    
    # 2. Parse ServiceNow JSON
    parser = ServiceNowParser()
    incidents = parser.parse_file(input_file)
    
    print(f"Loaded {len(incidents)} incidents from {input_file}")
    
    # 3. Select evaluator based on template
    evaluator_map = {
        'incident_logging': IncidentLoggingEvaluator,
        'incident_handling': IncidentHandlingEvaluator,
        'customer_service': CustomerServiceEvaluator
    }
    
    if template not in evaluator_map:
        print(f"Invalid template: {template}")
        sys.exit(1)
    
    EvaluatorClass = evaluator_map[template]
    evaluator = EvaluatorClass()
    
    # 4. Evaluate each incident
    results = []
    for i, incident in enumerate(incidents, 1):
        print(f"Evaluating {i}/{len(incidents)}: {incident['number']}")
        
        evaluation = evaluator.evaluate(incident)
        
        # Calculate score
        calculator = ScoreCalculator()
        score_result = calculator.calculate(evaluation)
        
        results.append({
            'incident': incident,
            'evaluation': evaluation,
            'score': score_result
        })
    
    # 5. Generate HTML reports
    output_dir = Path('reports')
    output_dir.mkdir(exist_ok=True)
    
    generator = HTMLReportGenerator(template=template)
    
    for result in results:
        incident_number = result['incident']['number']
        output_file = output_dir / f"{incident_number}_review.html"
        
        generator.generate(
            incident=result['incident'],
            evaluation=result['evaluation'],
            score=result['score'],
            output_path=output_file
        )
        
        print(f"Generated report: {output_file}")
    
    # 6. Summary
    print(f"\n{'='*60}")
    print("EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total tickets evaluated: {len(results)}")
    print(f"Reports generated in: {output_dir}")
    
    # Calculate averages
    avg_score = sum(r['score']['final_score'] for r in results) / len(results)
    pass_count = sum(1 for r in results if r['score']['percentage'] >= 90)
    
    print(f"Average score: {avg_score:.1f}/70 ({avg_score/70*100:.1f}%)")
    print(f"Pass rate: {pass_count}/{len(results)} ({pass_count/len(results)*100:.1f}%)")

if __name__ == '__main__':
    main()
```

---

## IMPLEMENTATION REQUIREMENTS

### Dependencies (requirements.txt)
```
anthropic>=0.40.0
jinja2>=3.1.2
language-tool-python>=2.7.1
plotly>=5.18.0
python-dateutil>=2.8.2
requests>=2.31.0
```

### Environment Variables (.env)
```bash
# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here

# Application Settings
LOG_LEVEL=INFO
OUTPUT_DIR=reports
BATCH_SIZE=10

# LLM Settings
MODEL_NAME=claude-sonnet-4-20250514
MAX_TOKENS=4000
TEMPERATURE=0.3
```

### Configuration (config.py)
```python
import os
from pathlib import Path
from dotenv import load_load_env()

# Anthropic API
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MODEL_NAME = os.getenv('MODEL_NAME', 'claude-sonnet-4-20250514')
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '4000'))
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.3'))

# Application
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'reports'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))

# Scoring
PASS_THRESHOLD = 63  # 90% of 70 points
MAX_SCORE = 70

# Band thresholds
BANDS = {
    'BLUE': 95.0,
    'GREEN': 90.0,
    'YELLOW': 75.0,
    'RED': 50.0,
    'PURPLE': 0.0
}
```

---

## SAMPLE DATA FOR TESTING

### Sample Incident 1: Perfect Score (INC8924218)
```json
{
  "number": "INC8924218",
  "contact_type": "phone",
  "state": "7",
  "category": "software",
  "subcategory": "reset_restart",
  "short_description": "MMC-NCL Bangalore-VDI-error message",
  "description": "Validated by: Okta Push MFA & Full Name\n\nContact Number:6361780076\n\nWorking remotely: Y\n\nIssue/Request: Colleague is getting error message while connecting to VDI which says, \"loading failed\"\n\nTS:\n->VDI reset/restart\n->asked colleague to login after 5-10 mins\n->Colleague confirmed that they can login now\nGot confirmation to close the ticket\n",
  "close_code": "Solved (Permanently)",
  "close_notes": ">VDI reset/restart\n->asked colleague to login after 5-10 mins\n->Colleague confirmed that they can login now\nGot confirmation to close the ticket\n",
  "priority": "5",
  "cmdb_ci": "cd0fa01c472e8910af5bebbd436d4319"
}
```

**Expected Evaluation:**
- Category: 10/10 ✓
- Subcategory: 10/10 ✓
- Short Description: 8/8 ✓ (4-part format correct)
- Description: 20/20 ✓ (complete validation, issue, troubleshooting)
- Spelling/Grammar: 2/2 ✓
- Validation: PASS ✓
- Resolution Notes: 15/15 ✓
- **Total: 70/70 (100%)**

---

## ERROR HANDLING

### Input Validation
```python
def validate_json_input(data):
    """
    Validate ServiceNow JSON structure
    """
    if 'records' not in data:
        raise ValueError("Missing 'records' key in JSON")
    
    if not isinstance(data['records'], list):
        raise ValueError("'records' must be a list")
    
    if len(data['records']) == 0:
        raise ValueError("No incidents found in JSON")
    
    # Validate required fields
    required_fields = ['number', 'category', 'short_description', 'description']
    for incident in data['records']:
        for field in required_fields:
            if field not in incident:
                raise ValueError(f"Missing required field '{field}' in incident {incident.get('number', 'unknown')}")
```

### LLM Error Handling
```python
def call_llm_with_retry(prompt, max_retries=3):
    """
    Call LLM API with retry logic
    """
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}]
            )
            return parse_json_response(response.content)
        
        except JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"JSON parse error, retrying... ({attempt+1}/{max_retries})")
                continue
            else:
                # Fallback: return default scores
                return get_default_evaluation()
        
        except Exception as e:
            print(f"LLM API error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                raise
```

---

## TESTING STRATEGY

### Unit Tests
```python
# tests/test_short_description.py

def test_valid_short_description():
    result = evaluate_short_description("Mercer - Boston - Domain Account - Password Reset", {})
    assert result['score'] == 8
    assert result['parts_correct'] == 4

def test_invalid_lob():
    result = evaluate_short_description("InvalidLOB - Boston - AD - Password Reset", {})
    assert result['score'] < 8
    assert 'Invalid LoB' in result['errors']

def test_too_many_words():
    result = evaluate_short_description("Mercer - Boston - AD - This is way too many words in description", {})
    assert 'too long' in str(result['errors'])
```

### Integration Tests
```python
# tests/test_full_evaluation.py

def test_full_incident_logging_evaluation():
    with open('tests/fixtures/sample_perfect_ticket.json') as f:
        data = json.load(f)
    
    incident = data['records'][0]
    evaluator = IncidentLoggingEvaluator()
    result = evaluator.evaluate(incident)
    
    calculator = ScoreCalculator()
    score = calculator.calculate(result)
    
    assert score['final_score'] == 70
    assert score['percentage'] == 100.0
    assert score['band'] == 'BLUE'
```

---

## DEPLOYMENT INSTRUCTIONS

### Installation
```bash
# 1. Clone repository
git clone https://github.com/your-org/ctss-ticket-reviewer.git
cd ctss-ticket-reviewer

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run tests
pytest tests/

# 6. Test with sample data
python main.py tests/fixtures/sample_tickets.json incident_logging
```

### Usage Examples
```bash
# Single template evaluation
python main.py tickets.json incident_logging

# Batch processing
python main.py last_week.json incident_handling

# Specific incidents only
python main.py --filter "INC8924218,INC8924339" tickets.json customer_service

# Output to specific directory
python main.py --output /path/to/reports tickets.json incident_logging

# Verbose mode
python main.py -v tickets.json incident_handling
```

---

## PERFORMANCE SPECIFICATIONS

### Expected Performance
- **Processing Speed:** 20-30 tickets/minute
- **LLM Calls:** 3-5 per ticket (depending on template)
- **Memory Usage:** <500MB for 100 tickets
- **Report Generation:** <1 second per ticket

### Optimization Strategies
1. **Batch LLM calls** when possible
2. **Cache** repeated evaluations (e.g., category validations)
3. **Parallel processing** for independent tickets
4. **Lazy loading** of templates and resources

---

## FUTURE ENHANCEMENTS

### Phase 2 Features
1. **Web Interface**
   - Upload JSON via browser
   - Real-time progress tracking
   - Interactive dashboards

2. **API Integration**
   - Direct ServiceNow API connection
   - Automated scheduled reviews
   - Real-time ticket scoring

3. **Machine Learning**
   - Train ML models on human-reviewed tickets
   - Improve accuracy over time
   - Predict analyst performance trends

4. **Advanced Analytics**
   - Team performance dashboards
   - Trend analysis over time
   - Coaching recommendation engine

### Phase 3 Features
1. **Five9 Integration**
   - Call recording analysis
   - Sentiment analysis
   - Automated quality scoring from audio

2. **Automated Feedback Loop**
   - Team lead corrections fed back to system
   - Continuous model improvement
   - A/B testing of evaluation strategies

---

## SUCCESS METRICS

### Accuracy Metrics
- **Target:** 90%+ agreement with human reviewers
- **Measurement:** Parallel run 50-100 tickets, compare scores
- **Acceptance:** <5% variance on 80% of tickets

### Efficiency Metrics
- **Time Savings:** 85-95% reduction vs manual
- **Volume:** Process 100+ tickets in <5 minutes
- **Availability:** 99.9% uptime for API-based system

### Quality Metrics
- **Consistency:** Same ticket = same score (100%)
- **Completeness:** All criteria evaluated (100%)
- **Actionability:** 90%+ of coaching feedback actionable

---

## SUPPORT & MAINTENANCE

### Logging
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ctss_reviewer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Monitoring
- Track API usage and costs
- Monitor evaluation accuracy
- Alert on errors or anomalies
- Track processing times

### Documentation
- API documentation (for future integrations)
- User manual for team leads
- Troubleshooting guide
- FAQ for common issues

---

## APPENDICES

### Appendix A: Complete Scoring Rubric JSON

See `/home/claude/scoring_rubrics.json` for machine-readable rubrics.

### Appendix B: Sample ServiceNow Data

See `/home/claude/prototype_samples.json` for 3 perfect sample tickets.

### Appendix C: Field Mapping

See `/home/claude/field_mapping.json` for complete field mappings.

---

## CONTACT & HANDOFF

**Project Team:**
- Dr. Michael Chen - Architecture & Infrastructure
- Dr. Alistair Finch - Process Intelligence & AI

**Next Steps:**
1. Review this specification
2. Set up development environment
3. Implement core parser and evaluator
4. Test with sample data
5. Generate first HTML reports
6. Iterate based on feedback

**Timeline:**
- Day 1-2: Core infrastructure and parsing
- Day 3-4: Rules engine and LLM integration
- Day 5: HTML report generation
- Day 6-7: Testing and refinement
- Day 8: Delivery and documentation

---

**END OF SPECIFICATION**

*This document contains all information necessary to build the CTSS Ticket Quality Review system. Good luck!*
