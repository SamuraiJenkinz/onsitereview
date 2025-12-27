# CTSS Ticket Quality Review - Claude Code Handoff Package

## 📦 Package Contents

This handoff package contains everything needed to build the CTSS Ticket Quality Review automation system.

### Files Included:

1. **CTSS_PROJECT_SPECIFICATION.md** ⭐ **START HERE**
   - Complete technical specification (60+ pages)
   - System architecture and data structures
   - Detailed scoring rubrics for all three templates
   - Code examples and implementation guidance
   - Testing strategy and deployment instructions

2. **scoring_rubrics.json**
   - Machine-readable scoring criteria
   - All three templates (Incident Logging, Handling, Customer Service)
   - Point values and scoring options
   - Critical for building the evaluation engine

3. **prototype_samples.json**
   - 3 perfect sample tickets from real ServiceNow data
   - All have 100/100 quality scores
   - Use these for testing and validation
   - Representative of actual production data

## 🚀 Quick Start for Claude Code

### Step 1: Read the Specification
Open `CTSS_PROJECT_SPECIFICATION.md` and review:
- Executive Summary (page 1)
- System Architecture (page 2-3)
- Scoring Rubrics (pages 10-25)
- Data Structure (pages 4-9)

### Step 2: Understand the Goal
Build a Python application that:
1. Parses ServiceNow JSON exports
2. Evaluates tickets using rules + LLM
3. Generates professional HTML reports
4. Scores on 70-point scale with performance bands

### Step 3: Start Building
Recommended build order:
1. **JSON Parser** (Day 1)
   - Parse ServiceNow JSON format
   - Extract and normalize fields
   - Handle 3,831 ticket dataset

2. **Rules Engine** (Day 2)
   - Category/subcategory validation
   - Short description format checker
   - Spelling/grammar validation
   - Validation detection

3. **LLM Evaluator** (Day 3)
   - Anthropic Claude API integration
   - Structured prompt templates
   - JSON response parsing
   - Troubleshooting quality assessment

4. **Scoring Calculator** (Day 4)
   - Point calculation
   - Deduction logic (validation, critical process)
   - Performance band assignment

5. **HTML Report Generator** (Day 5)
   - Jinja2 templates
   - Tailwind CSS styling
   - Plotly visualizations
   - Coaching recommendations

6. **Testing & Refinement** (Day 6-7)
   - Test with prototype_samples.json
   - Validate against expected scores
   - Generate sample reports

## 📋 Key Requirements

### Must Have:
- ✅ Python 3.12+
- ✅ Anthropic API key (Claude Sonnet 4)
- ✅ Dependencies: anthropic, jinja2, language-tool-python, plotly

### Architecture:
```
Input: ServiceNow JSON → Parser → Evaluator (Rules + LLM) → Scorer → HTML Report
```

### Templates to Build:
1. **Incident Logging** (70 pts) - Focus on documentation quality
2. **Incident Handling** (70 pts) - Focus on troubleshooting and resolution
3. **Customer Service** (70 pts) - Focus on soft skills and customer interaction

## 🎯 Success Criteria

Your implementation should:
- ✅ Parse the provided JSON samples without errors
- ✅ Score INC8924218 at 100/100 (perfect ticket)
- ✅ Generate professional HTML reports
- ✅ Complete evaluation in <2 minutes per ticket
- ✅ Match expected scores within ±5% variance

## 📊 Sample Data Summary

The `prototype_samples.json` contains:

**INC8924218** - Phone, VDI Issue
- Category: software > reset_restart
- Validation: ✓ OKTA Push
- Troubleshooting: ✓ Documented
- Resolution: ✓ Complete
- **Expected Score: 70/70 (100%)**

**INC8924339** - Phone, Password Reset
- Category: inquiry > password reset  
- Validation: ✓ OKTA Push
- Critical Process: ✓ Password reset
- **Expected Score: 70/70 (100%)**

**INC8923651** - Phone, Password Reset
- Category: inquiry > password reset
- Validation: ✓ OKTA Push
- Critical Process: ✓ Password reset
- **Expected Score: 70/70 (100%)**

## 💡 Implementation Tips

### For the JSON Parser:
- Handle both sys_id references and display values
- Some fields may be empty (work_notes, comments)
- Parent/child incidents may be in different fields
- Contact type is critical for evaluation routing

### For the LLM Evaluator:
- Use structured prompts with JSON schema output
- Include specific scoring rubric in each prompt
- Request evidence/reasoning for each score
- Implement retry logic for API failures

### For HTML Reports:
- Use Tailwind CDN (no build process needed)
- Include Plotly gauge charts for visual appeal
- Color-code performance bands (BLUE/GREEN/YELLOW/RED/PURPLE)
- Make coaching recommendations actionable

### For Testing:
- Start with INC8924218 (simplest perfect ticket)
- Validate each criterion individually
- Compare your scores to expected values in spec
- Generate HTML and visually inspect

## 🔗 Reference Links

**In the Specification:**
- Page 4-9: ServiceNow Data Structure
- Page 10-16: Incident Logging Rubric
- Page 17-21: Incident Handling Rubric  
- Page 22-25: Customer Service Rubric
- Page 34-42: LLM Prompt Examples
- Page 43-48: HTML Report Template

## 🚨 Critical Reminders

1. **Validation Deduction:** -15 points if not documented properly, FAIL if not performed
2. **Critical Process:** -35 points for failures, FAIL for password process violations
3. **Minimum Score:** Always cap at 0 (never negative)
4. **Pass Threshold:** 63/70 points (90%)
5. **Short Description:** Must be 4-part format: [LoB] - [Location] - [App] - [Brief]

## 📝 Notes from Dr. Chen & Dr. Finch

**Chen:** "The data quality is excellent - 3,831 closed tickets, all with validation and resolution data. Focus on getting the parser right first, everything else follows."

**Finch:** "This is a classic hybrid AI system - 40% rules, 60% LLM. The rules give you speed and consistency, the LLM gives you nuance and coaching insights. Don't skip the rules engine."

**Both:** "We've done all the analysis. The rubrics are clear, the data is clean, the architecture is proven. You've got everything you need. Build with confidence!"

---

## ✅ Pre-Flight Checklist

Before you start coding:
- [ ] Read CTSS_PROJECT_SPECIFICATION.md (at least Executive Summary and Architecture)
- [ ] Review scoring_rubrics.json structure
- [ ] Open prototype_samples.json and inspect ticket format
- [ ] Understand the 4-part short description requirement
- [ ] Know the difference between validation PASS/-15/FAIL
- [ ] Understand critical process deductions (-35 vs FAIL)

---

**Ready to build?** Start with the specification document and work through it section by section. You've got this! 🚀

**Questions?** Everything is in the spec. If something's unclear, re-read that section - we've been very thorough.

**Timeline:** Realistically 5-7 days for a complete working system with all three templates.

---

*Good luck from Dr. Chen and Dr. Finch!*
