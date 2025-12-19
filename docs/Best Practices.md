# Best Practices Guide: Metadata Harmonisation Tool

**Version:** 1.0  
**Last Updated:** December 2025  
**Target Audience:** Consortium members, data managers, researchers, and technical staff

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Data Quality Standards](#3-data-quality-standards)
4. [Codebook Development](#4-codebook-development)
5. [Variable Mapping Workflow](#5-variable-mapping-workflow)
6. [AI Model Configuration](#6-ai-model-configuration)
7. [Security and Privacy](#7-security-and-privacy)
8. [Collaboration and Governance](#8-collaboration-and-governance)
9. [Quality Assurance](#9-quality-assurance)
10. [Troubleshooting Common Issues](#10-troubleshooting-common-issues)
11. [Appendix](#11-appendix)

---

## 1. Introduction

### 1.1 Purpose of This Guide

This document provides practical guidance for using the Metadata Harmonisation Tool effectively and consistently across DS-I Africa consortium organizations. Whether you're a data manager with limited technical experience or a researcher working with complex health datasets, this guide will help you achieve high-quality data harmonisation.

### 1.2 What is the Metadata Harmonisation Tool?

The Metadata Harmonisation Tool is an AI-powered platform that helps match variables from incoming datasets to a standardized target codebook. It dramatically reduces the time needed for data harmonisation by:

- **Automatically generating variable descriptions** using Large Language Models (LLMs)
  -  If your study variable descriptions are missing or incomplete, the tool can propose draft descriptions using your uploaded context (e.g., protocols/data dictionaries).
  -  Better descriptions lead to better recommendations and reduce the amount of manual interpretation.
- **Recommending likely variable matches** based on semantic similarity
  -  The tool compares the “meaning” of variable names/descriptions to propose which target codebook variable is the best match.
  -  This speeds up harmonisation by reducing the number of manual searches through the codebook.
- **Supporting transformation rule creation** to align data formats
  -  When a variable matches conceptually but differs in units/coding (e.g., cm vs m, 1/2 vs Male/Female), the tool supports defining a conversion rule.
  -  Correct transformations ensure comparable values across studies after mapping.
- **Providing confidence scores** for mapping recommendations
  -  Each recommendation comes with a score to help you decide when to trust it and when to review more carefully.
  -  Confidence scores help prioritise human review effort (but do not replace review).

### 1.3 Key Benefits

- **Speed:** Reduces manual mapping time by up to 80%
  -  The tool provides an initial shortlist of candidate mappings so you spend less time searching.
- **Consistency:** Ensures uniform data structures across multiple studies
  -  Different studies can be mapped to the same target codebook, enabling pooled analysis.
  -  Consistency reduces rework and makes multi-site reporting more reliable.
- **Quality:** AI-powered recommendations reduce human error
  -  The tool helps catch obvious mismatches and suggests likely correct targets.
  -  It lowers the chance of accidental mapping to a similarly named but different concept.
- **Transparency:** All mappings are documented and auditable
  -  Outputs and logs can be used to track what was mapped, when, and by whom.
  -  This supports peer review, governance, and reproducibility.
- **Flexibility:** Supports multiple AI providers (local and cloud-based)
  -  You can use local Ollama for privacy-sensitive work or cloud providers for higher accuracy where permitted.
  -  This allows each consortium member to choose an option that fits their governance and resources.

---

## 2. Getting Started

### 2.1 Access Requirements

**For Non-Technical Users:**
- Web browser (Chrome, Firefox, Safari, or Edge)
- Access to a running installation (either an organization-provided URL or `http://localhost:8501` for local laptop installations)
- Basic understanding of your dataset's variables

**For Technical Users:**
- Docker and Docker Compose installed (recommended)
- Python 3.9+ environment (alternative setup)
- Local Ollama installation or cloud API keys

### 2.2 First-Time Setup

**Recommended for consortium members (local laptop self-install):** run the tool locally on your laptop and access it at `http://localhost:8501`. This avoids sharing data over the internet when using local Ollama.

**Installation (technical):** follow the repository `README.md` section “Getting Started (Recommended: Docker)” and `docker/README.md` (Windows quick start). If someone else has already installed it for you, skip installation and continue below.

#### Step 1: Choose Your AI Provider

The tool supports multiple AI providers:

| Provider | Best For | Requirements | Cost |
|----------|----------|--------------|------|
| **Ollama (Local)** | Privacy-sensitive data, no internet required | Local installation, 8GB+ RAM | Free |
| **OpenAI** | High accuracy, fastest processing | API key, internet connection | Pay per use |
| **Anthropic Claude** | Complex reasoning tasks | API key, internet connection | Pay per use |
| **Azure OpenAI** | Enterprise compliance | Azure subscription | Enterprise pricing |

**Recommendation for Consortium Members:** Start with Ollama for privacy-sensitive health data. Use cloud providers for non-sensitive pilot studies or when higher accuracy is needed.

#### Step 2: Configure Your Environment

1. Access the tool via your organization's provided URL (typically `http://localhost:8501` for local installations)
2. Navigate to the sidebar → **AI Configuration**
3. Select your AI provider and test the connection
4. Set appropriate timeout values (default: 30 seconds; increase to 60–120 seconds if your machine is slow or your model is large)

#### Step 3: Understand the Workflow

```
Upload Codebook → Upload Studies → Initialise → Map Studies → Download Results
```

**Where your work is saved (local laptop):** uploaded files and outputs are stored under `input/`, `results/`, and `logs/` in the project folder.

### 2.3 Quick Start Checklist

- [ ] Access to the Metadata Harmonisation Tool
  -  You can open the tool in a web browser and see the navigation sidebar.
  -  If you cannot access the tool, none of the later steps (uploads, initialise, mapping, download) can be completed.
  - How to verify: Open the URL in your browser and confirm the page loads and you can see the sidebar sections/pages.
- [ ] Target codebook prepared (CSV format)
  -  You have a CSV that defines the “target” variables you want all studies mapped to.
  -  The tool can only recommend mappings to variables that exist in the target codebook.
  - How to verify: Open the CSV and confirm it contains at least `variable_name` and `description` columns, with one row per target variable.
- [ ] Dataset variables documented
  -  You have a CSV listing the variables in your incoming dataset (the study you want to harmonise).
  -  Recommendations are made variable-by-variable; the tool needs a clear list of what variables exist in the study.
  - How to verify: Confirm your variables file contains at least `variable_name` (matching your dataset’s column headers) and a `description` column (can be empty if you provide supporting documents).
- [ ] Example data available (optional but recommended)
  -  You have a small de-identified sample of the study data (a CSV with the same column headers as `variable_name`).
  -  Example values help humans validate that a proposed mapping (and any transformation) makes real-world sense.
  - How to verify: Confirm the example data column headers match your variables CSV `variable_name` values exactly.
- [ ] Study protocol or documentation available (optional)
  -  You have supporting documents (e.g., protocol, data dictionary, CRF) describing how variables were collected and coded.
  -  When descriptions are missing or ambiguous, documentation provides the context needed to interpret variables correctly.
  - How to verify: Ensure the document(s) are ready to upload and contain definitions/coding schemes (e.g., what “1/2/3” means).
- [ ] AI provider configured and tested
  -  You selected an AI provider in the sidebar and confirmed the connection works.
  -  Description generation and recommendations depend on the AI provider being reachable and correctly configured.
  - How to verify: In **AI Configuration**, click the connection test and confirm you get a successful status (no connection errors/timeouts).

---

## 3. Data Quality Standards

### 3.1 Input Data Requirements

#### Target Codebook Standards

Your target codebook MUST include required columns and MAY include optional columns for enhanced functionality:

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `variable_name` | **Yes** | Unique identifier for the variable | `patient_age` |
| `description` | **Yes** | Clear, detailed description | "Patient's age in completed years at enrollment" |
| `dType` | Optional | Data type of the variable | `integer`, `float`, `string`, `boolean`, `datetime` |
| `Unit` | Optional | Unit of measurement | `years`, `kg`, `cm`, `YYYY-MM-DD`, `hh:mm:ss` |
| `Categories` | Optional | Allowed categorical values (pipe-separated) | `Male\|Female\|Other` |
| `Unit Example` | Optional | Example value in the specified unit | `62`, `2023/06/26`, `BA112` |

**Supported Data Types (dType):**
- `float` - Decimal numbers (e.g., height, BMI)
- `integer` - Whole numbers (e.g., age, count)
- `string` - Text values (e.g., identifiers, names)
- `boolean` - True/False values
- `datetime` - Date and time values

*Note: Other dType values are accepted but default handling applies*

**Best Practices:**
- Use snake_case for variable names (e.g., `blood_pressure_systolic`)
  -  Consistent naming makes it easier to match variables across studies and reduces ambiguity.
  - How to verify: Variable names use lowercase letters, numbers, and underscores (no spaces).
- Keep descriptions concise but informative (under 500 characters)
  -  Clear descriptions improve recommendation quality and help reviewers understand variables quickly.
  - How to verify: A colleague should be able to understand the variable without opening the raw dataset.
- **Always specify dType** when available for better validation
  -  dType helps identify mismatches early (e.g., mapping a string ID to a numeric target).
  - How to verify: For each variable, confirm dType reflects how the data is stored (not just how you *wish* it was stored).
- **Include Unit** for all numeric and temporal variables
  -  Units are essential for correct transformations (e.g., cm vs m; mg/dL vs mmol/L).
  - How to verify: If a variable is numeric, you can answer “what unit is this measured in?” (or explicitly set Unit to `None` if truly unitless).
- **Define Categories** for categorical/enumerated variables (use pipe `|` as separator)
  -  Explicit categories reduce misinterpretation and make recoding/validation safer.
  - How to verify: The categories list includes all expected values (including Unknown/Not applicable when used).
- **Provide Unit Example** to clarify expected format
  -  Examples help detect formatting differences (e.g., date formats, ID patterns).
  - How to verify: The Unit Example looks like a real value that would appear in the dataset.
- Reference standardized ontologies when possible (e.g., SNOMED-CT, LOINC)
  -  Standards reduce semantic drift and make multi-site harmonisation more consistent.
  - How to verify: If a variable maps to a known clinical concept, include the standard label/code in the description where appropriate.
- Use ISO standards for dates (YYYY-MM-DD) and times (hh:mm:ss)
  -  Standard formats prevent parsing errors and reduce ambiguity across countries.
  - How to verify: Your date/time examples match the stated format.

**Example - Minimum Required Format:**
```csv
variable_name,description
patient_id,"Unique identifier assigned to each patient at enrollment"
enrollment_date,"Date when patient was enrolled in the study"
hiv_status,"HIV infection status at baseline"
cd4_count,"CD4+ T-cell count measured within 30 days of enrollment"
```

**Example - Enhanced Format (Recommended):**
```csv
variable_name,description,dType,Unit,Categories,Unit Example
patient_id,"Unique identifier assigned to each patient",string,None,None,BA112
enrollment_date,"Date when patient was enrolled in the study",datetime,YYYY-MM-DD,None,2023/06/26
dob,"Date of birth",datetime,YYYY-MM-DD,None,1990/03/15
country,"Country code",string,ISO 3166-1 alpha-3,None,ZAF
age_enrolment,"Age in completed years at enrollment",integer,years,None,33
sex,"Biological sex",string,categorical,Male|Female|Intersex,Male
gender_identity,"Gender identity",string,categorical,Male|Female|Non-binary|Other|Prefer not to say,Female
height_cm,"Height measured in centimeters",float,cm,None,165.5
weight_kg,"Body weight measured in kilograms",float,kg,None,72.3
bmi,"Body Mass Index",float,kg/m2,None,26.5
bp_systolic,"Systolic blood pressure",integer,mmHg,None,120
bp_diastolic,"Diastolic blood pressure",integer,mmHg,None,80
hiv_status,"HIV infection status at baseline",string,categorical,Positive|Negative|Unknown,Positive
on_art,"Currently on antiretroviral therapy",boolean,True/False,True|False,True
cd4_count,"CD4+ T-cell count",integer,cells/μL,None,350
viral_load,"HIV viral load",integer,copies/mL,None,50
pregnancy_status,"Pregnancy status at enrollment",string,categorical,Pregnant|Not pregnant|Unknown,Not pregnant
```

#### Dataset Variables Standards

Your incoming dataset variables CSV **must** include the same required columns:

| Column | Required | Description | Notes |
|--------|----------|-------------|-------|
| `variable_name` | **Yes** | Original variable name from your dataset | Must match exactly with column names in example data |
| `description` | **Yes** | Variable description | **May be empty** - AI can generate if missing |

**Optional columns** (same as codebook):
- `dType` - Data type (recommended for validation)
- `Unit` - Unit of measurement
- `Categories` - Allowed values for categorical variables
- `Unit Example` - Sample value

**Best Practices:**
- Provide descriptions whenever possible to improve matching accuracy
  -  Recommendations are strongest when descriptions capture meaning, population, timing, and units.
  - How to verify: For each variable, the description answers “what is this, when is it measured, and in what unit/coding?”.
- If descriptions are missing, upload supporting documents (study protocols, data dictionaries)
  -  Documentation provides context that can be used to interpret variables and generate draft descriptions.
  - How to verify: The supporting document includes variable definitions, coding schemes, and/or CRF sections.
- Include dType and Unit for better semantic matching
  -  Type + unit constraints help reviewers spot wrong matches and guide transformations.
  - How to verify: Numeric variables have units; categorical variables have categories.
- **Ensure variable_name matches exactly** with column headers in example data CSV
  -  If names don’t match exactly, example values won’t display correctly and transformation validation becomes unreliable.
  - How to verify: Copy/paste a `variable_name` into the example data header list and confirm it appears exactly once.
- Document missing value codes (e.g., -99, NA, NULL, 999) in descriptions
  -  Missing codes can be mistaken for real values and corrupt transformations/statistics.
  - How to verify: The description (or a note) explicitly lists missing codes used in that variable.

**Example - Minimal Format:**
```csv
variable_name,description
pt_id,
visit_dt,
hiv_stat,
```
*Note: Empty descriptions will be generated by AI if supporting documents are provided*

**Example - Complete Format:**
```csv
variable_name,description,dType,Unit,Categories,Unit Example
pt_id,"Patient identifier",string,None,None,P001
visit_dt,"Visit date",datetime,YYYY-MM-DD,None,2023/06/26
age,"Age at visit",integer,years,None,45
hiv_stat,"HIV status",string,categorical,POS|NEG|UNK,POS
```

### 3.2 Data Completeness

**Example Data CSV (Optional but Recommended):**

The example data CSV helps the mapping process by allowing you to:
- Quickly sanity-check what a variable looks like (ranges, missingness, categories)
- Preview and validate transformation rules (Transform Mode)

**Critical Requirement:** 
⚠️ **Column names in example data CSV MUST match `variable_name` exactly** from your variables CSV

**Example:**

If your variables CSV has:
```csv
variable_name,description,dType
patient_id,"Patient identifier",string
age_enrolment,"Age at enrollment",integer
sex,"Sex",string
```

Your example data CSV must have matching column headers:
```csv
patient_id,age_enrolment,sex
BA112,62,Female
BA113,45,Male
BA114,38,Female
```

**Best Practices for Example Data:**
- Include at least 100 representative records
  -  Too-small samples can hide category values and make distributions misleading.
  - How to verify: The sample includes enough rows to show common categories and realistic ranges.
- Remove all personally identifiable information (PII)
  -  Example data is only needed for value-shape validation; PII should not be included.
  - How to verify: No names, phone numbers, national IDs, addresses, exact GPS, or free-text notes containing identifiers.
- Include diverse examples (e.g., different age groups, conditions)
  -  Diversity helps you test transformations against realistic edge cases.
  - How to verify: You can find examples across the expected range (min/max) and across key categories.
- Maintain realistic distributions
  -  Unrealistic samples can mislead reviewers into rejecting correct mappings.
  - How to verify: Basic summaries (min/max/mean and category counts) look plausible compared to the real dataset.
- Include examples of edge cases (minimum/maximum values)
  -  Edge cases are where transformations and validation rules often fail.
  - How to verify: The sample includes known extremes and boundary values.
- Show how missing values are coded (e.g., -99, NA, NULL)
  -  Reviewers need to know whether values like -99 are “missing” or “real”.
  - How to verify: Missing codes appear in the sample (if used) and match what is documented.
- Document any transformations applied
  -  If sample data has already been cleaned/recoded, reviewers must know so they don’t infer wrong units/codings.
  - How to verify: A short note indicates whether the sample is raw, cleaned, or derived.

**Minimum Requirements:**
- At least 70% of variables should have descriptions (or supporting documents)
- Example data should include at least 100 representative records (if provided)
- Missing value codes should be documented (e.g., -99, NA, NULL)

**Quality Indicators:**
- ✅ **Excellent:** >90% variables with descriptions, example data provided, supporting documents
- ⚠️ **Good:** 70-90% variables with descriptions, example data OR supporting documents
- ❌ **Poor:** <70% variables with descriptions, no supporting information

### 3.3 Handling Missing Information

If your dataset lacks variable descriptions:

1. **Upload Study Protocol:** The AI can extract relevant context
2. **Use Example Data:** Example values can help you interpret ambiguous variables and validate transformations
3. **Document Domain Knowledge:** Add notes about data collection procedures
4. **Review Generated Descriptions:** Always validate AI-generated content

---

## 4. Codebook Development

### 4.1 Designing Effective Codebooks

A well-designed target codebook is crucial for successful harmonisation. Follow these principles:

#### Principle 1: Clarity and Precision

**Good Example:**
```
variable_name: temperature_celsius
description: Body temperature measured in degrees Celsius using a digital thermometer, recorded to one decimal place (e.g., 36.5°C)
```

**Poor Example:**
```
variable_name: temp
description: Temperature
```

#### Principle 2: Standardization

- Use internationally recognized standards:
  -  Standards make variable meaning consistent across sites and simplify downstream analysis.
  - **Clinical data:** OMOP CDM, FHIR resources
  - **Lab results:** LOINC codes
  - **Diagnoses:** ICD-10, SNOMED-CT
  - **Medications:** RxNorm, ATC codes

#### Principle 3: Categorical Variables

When defining categorical variables, use the `Categories` column with pipe-separated values:

**Format:** `Value1|Value2|Value3`

**Best Practices:**
- List all possible values explicitly
  -  Hidden/unknown values often cause mapping and transformation errors later.
  - How to verify: The categories list includes all expected values, including Unknown/Not applicable when used.
- Use consistent capitalization (e.g., "Male|Female" not "male|Female")
  -  Mixed capitalization can create false “new categories” and break recoding rules.
  - How to verify: The same concept uses the same exact spelling/case everywhere.
- Avoid spaces before/after pipes: ❌ `Male | Female` → ✅ `Male|Female`
  -  Extra spaces can create category values like " Male" that don’t match what you expect.
  - How to verify: No spaces around `|` separators.
- Include "Unknown" or "Not specified" when appropriate
  -  Real datasets often contain unknown/missing categorical responses that need explicit handling.
  - How to verify: If the study uses an unknown code/value, it is represented in `Categories`.
- Use full words rather than codes when possible for clarity
  -  Full labels are easier to review and less likely to be misinterpreted across sites.
  - How to verify: If codes must be used, document them clearly in the description (e.g., 1=Male, 2=Female).

**Examples:**

✅ **Good:**
```csv
variable_name,description,dType,Categories
hiv_status,"HIV status",string,Positive|Negative|Unknown
sex,"Biological sex",string,Male|Female|Intersex
pregnancy_status,"Pregnancy status",string,Pregnant|Not pregnant|Unknown|Not applicable
```

❌ **Poor:**
```csv
variable_name,description,dType,Categories
hiv_status,"HIV status",string,P|N|U
sex,"Sex",string,m|f
pregnancy_status,"Pregnancy",string,yes|no
```

#### Principle 4: Units and Examples

**Unit Column:**
Specify the unit of measurement for all numeric and temporal variables. This helps:
- Ensure consistent interpretation across datasets
- Enable automatic unit conversion when needed
- Validate data ranges and detect errors

**Common Units by Variable Type:**

| Variable Type | Unit Examples | Format Notes |
|---------------|---------------|--------------|
| Age | `years`, `months`, `days` | Use singular form |
| Weight/Mass | `kg`, `g`, `lbs` | SI units preferred |
| Height/Length | `cm`, `m`, `inches` | SI units preferred |
| Temperature | `°C`, `°F`, `K` | Specify scale |
| Time | `hh:mm:ss`, `seconds`, `minutes` | Use standard format |
| Date | `YYYY-MM-DD`, `DD/MM/YYYY` | ISO 8601 preferred |
| Concentration | `cells/μL`, `mg/dL`, `mmol/L` | Include denominator |
| Pressure | `mmHg`, `kPa` | Specify unit |
| Percentage | `%`, `proportion (0-1)` | Specify range |

**Unit Example Column:**
Provide a realistic example value that demonstrates:
- Expected format
- Typical value range
- Precision (decimal places)
- Format for identifiers or codes

**Examples:**

```csv
variable_name,description,dType,Unit,Categories,Unit Example
temperature_c,"Body temperature",float,°C,None,37.2
date_enrolled,"Enrollment date",datetime,YYYY-MM-DD,None,2023/06/26
visit_time,"Visit time",datetime,hh:mm:ss,None,14:30:00
patient_id,"Patient identifier",string,None,None,PAT-001-2023
country_code,"Country code",string,ISO 3166-1 alpha-3,None,ZAF
lab_result_unit,"Lab result unit",string,categorical,mg/dL|mmol/L|g/L,mg/dL
```

**Special Cases:**
- For categorical string variables: Set Unit to `categorical` and list values in Categories
- For identifiers/codes: Set Unit to `None` and provide format example in Unit Example
- For percentages: Clarify if 0-100 scale or 0-1 proportion

#### Principle 5: Versioning

Maintain version control for your codebook:
- Use semantic versioning (e.g., v1.0.0, v1.1.0, v2.0.0)
- Document all changes in a CHANGELOG
- Archive previous versions
- Communicate changes to all consortium members

### 4.2 Codebook Structure Templates

#### Minimum Viable Codebook (Required Columns Only)
```csv
variable_name,description
study_id,"Unique study identifier"
participant_id,"Unique participant identifier within study"
visit_date,"Date of study visit"
```

#### Enhanced Codebook (Recommended - All Columns)
```csv
variable_name,description,dType,Unit,Categories,Unit Example
study_id,"Unique study identifier",string,None,None,STU001
participant_id,"Unique participant identifier within study",string,None,None,P001
visit_date,"Date of study visit",datetime,YYYY-MM-DD,None,2023/06/26
visit_time,"Time of visit",datetime,hh:mm:ss,None,12:12:12
dob,"Date of birth",datetime,YYYY-MM-DD,None,1990/03/15
country,"Country of enrollment",string,ISO 3166-1 alpha-3,None,ZAF
age_years,"Age in completed years at enrollment",integer,years,None,33
sex,"Biological sex",string,categorical,Male|Female|Intersex,Male
gender_identity,"Gender identity",string,categorical,Male|Female|Non-binary|Other|Prefer not to say,Female
height_cm,"Height measured in centimeters",float,cm,None,165.5
weight_kg,"Body weight measured in kilograms",float,kg,None,72.3
bmi,"Body Mass Index",float,kg/m2,None,26.5
bp_systolic,"Systolic blood pressure",integer,mmHg,None,120
bp_diastolic,"Diastolic blood pressure",integer,mmHg,None,80
hiv_status,"HIV infection status at baseline",string,categorical,Positive|Negative|Unknown,Positive
on_art,"Currently on antiretroviral therapy",boolean,True/False,True|False,True
cd4_count,"CD4+ T-cell count",integer,cells/μL,None,350
viral_load,"HIV viral load",integer,copies/mL,None,50
pregnancy_status,"Pregnancy status at enrollment",string,categorical,Pregnant|Not pregnant|Unknown,Not pregnant
```

#### Data Type Reference Guide

Use these guidelines when specifying `dType`:

| dType | Use For | Unit Examples | Categories Examples |
|-------|---------|---------------|---------------------|
| `string` | Text, IDs, codes | None, ISO codes | Country codes, status values |
| `integer` | Whole numbers, counts | years, kg, cells/μL | None (use Categories for categorical integers) |
| `float` | Decimal numbers | cm, kg/m2, % | None |
| `boolean` | Yes/No, True/False | True/False, Yes/No | True\|False, Yes\|No |
| `datetime` | Dates and times | YYYY-MM-DD, hh:mm:ss, ISO 8601 | None |

### 4.3 Domain-Specific Guidelines

#### For Epidemiological Studies
- Include standardized sociodemographic variables (age, sex, ethnicity)
- Use WHO case definitions for diseases
- Align with minimal data sets for emergency response (MDN)

#### For Clinical Trials
- Follow ICH E6(R2) GCP guidelines
- Include required regulatory variables
- Map to CDISC SDTM domains where applicable

#### For Genomics Data
- Use standardized nomenclature (HGVS for variants)
- Include reference genome version
- Specify sequencing platform and quality metrics

---

## 5. Variable Mapping Workflow

### 5.1 Pre-Mapping Preparation

#### Step 1: Data Inventory
Create an inventory of your dataset:
- Total number of variables
  -  This helps you estimate time/effort and decide whether to work in batches.
- Variables with/without descriptions
  -  Missing descriptions usually require supporting documents or more manual review.
- Data types present
  -  Types (e.g., numeric vs categorical) affect which target variables make sense and which transformations are needed.
- Known data quality issues
  -  Known problems (e.g., inconsistent coding) should be resolved or documented before mapping.

#### Step 2: Context Documentation
Document important context:
- Study design and objectives
  -  The same variable name can mean different things depending on study design.
- Data collection methods
  -  Collection method often determines units, timing, and expected value ranges.
- Known coding schemes
  -  Many errors come from recoding (e.g., 1/2/3 representing categories differently across studies).
- Special considerations or limitations
  -  Notes about missingness, changes over time, or site differences help reviewers interpret mappings correctly.

#### Step 3: Example Data Preparation
Prepare representative example data:
- Remove all personally identifiable information (PII)
  -  Example data is for validation and should not expose sensitive details.
- Include diverse examples (e.g., different age groups, conditions)
  -  Diversity helps reveal edge cases and category values that may not appear in a small biased sample.
- Maintain realistic distributions
  -  Unrealistic data can make correct mappings look incorrect (or vice versa).
- Document any transformations applied
  -  If the example data is already processed, reviewers need to know what was changed.

### 5.2 Using the Recommendation Engine

#### Understanding Confidence Scores

The tool provides confidence scores for each recommended mapping:

| Score Range | Interpretation | Action Required |
|-------------|----------------|-----------------|
| 90-100% | Very high confidence | Review and approve |
| 70-89% | High confidence | Verify mapping is correct |
| 50-69% | Moderate confidence | Careful review needed |
| <50% | Low confidence | Likely requires manual mapping |

#### Interpreting Recommendations

The recommendation algorithm considers:
1. **Semantic similarity of embeddings**: variable descriptions (higher weight) and variable names (lower weight)

**When to trust recommendations:**
- High confidence score (>80%)
- Variable names are semantically similar
- Descriptions align well
- Example values (if provided) look plausible for the chosen target variable

**When to be cautious:**
- Low confidence score (<70%)
- Multiple similar recommendations
- Conceptually different variables

### 5.3 Manual Mapping Best Practices

#### Review Process

For each variable mapping:

1. **Check semantic alignment:**
   - Do the descriptions match conceptually?
   - Are the data types compatible?
   - Do units of measurement align?

2. **Verify with example data:**
   - Compare value ranges
   - Check for outliers or impossible values
   - Verify coding schemes match

3. **Document decisions:**
   - Note any assumptions made
   - Flag uncertain mappings for team review
   - Record transformation rules needed

#### Common Mapping Scenarios

**Scenario 1: Direct Match**
```
Source: patient_age → Target: age_years
Action: Accept recommendation ✓
```

**Scenario 2: Unit Conversion Needed**
```
Source: height_cm → Target: height_m
Action: Apply transformation rule: x/100
```

**Scenario 3: Recoding Required**
```
Source: sex_code → Target: gender_text
Action: Create categorical mapping: {1: "Male", 2: "Female"}
```

**Scenario 4: No Clear Match**
```
Source: custom_score → Target: (no equivalent)
Action: Document as unmapped, consult with team
```

### 5.4 Quality Checks During Mapping

Run these checks periodically:

- [ ] All high-priority variables mapped
  -  Variables that are essential for analysis/reporting have a confirmed mapping (or a documented reason why not).
  -  Missing high-priority variables usually blocks downstream analysis and creates inconsistencies across studies.
  - How to verify: Confirm no high-priority variables are left “To do” or unmapped without rationale.
- [ ] Confidence scores reviewed
  -  You checked whether the tool’s top recommendations are high confidence or require careful manual review.
  -  A high score can still be wrong if two concepts are similar; a low score can still be correct in messy datasets.
  - How to verify: Spot-check a sample of high-confidence and low-confidence mappings against your documentation and example values.
- [ ] Transformation rules tested
  -  Any unit conversions or recoding rules produce valid outputs when applied.
  -  A correct mapping with an incorrect transformation can silently corrupt values.
  - How to verify: Apply transformations and check a few rows (including edge cases like missing values) for expected results.
- [ ] Edge cases handled (missing values, outliers)
  -  You considered special values (e.g., -99, 999), blanks, and out-of-range values and decided how they should be treated.
  -  Edge cases are a common source of incorrect transformations and misleading analyses.
  - How to verify: Test transformations and validation checks on those edge-case rows.
- [ ] Team consensus on uncertain mappings
  -  Ambiguous variables (or borderline matches) were reviewed with a second person/domain expert.
  -  This reduces systematic errors that occur when one mapper makes an assumption alone.
  - How to verify: Record the decision and rationale in a shared mapping log (or in the audit/decision log template).
- [ ] Documentation complete
  -  The reasons behind each non-obvious mapping and transformation are written down.
  -  Documentation allows another person to reproduce and trust the harmonisation decisions later.
  - How to verify: Confirm you have a mapping decision log, and that “special cases” and unmapped variables have a short rationale.

---

## 6. AI Model Configuration

### 6.1 Choosing the Right Model

#### For Description Generation

**Recommended Models:**
- **Ollama (llama3.1:8b):** Good balance of quality and speed for local use
  -  Runs locally on your machine (no third-party API), which can be preferable for sensitive work.
  -  Local inference typically reduces data-sharing risk and avoids per-request costs.
  - How to verify: The model is available in Ollama and the **AI Configuration** connection test succeeds.
- **OpenAI (gpt-4):** Best quality for complex medical terminology
  -  Uses a cloud-hosted model accessed via an API key.
  -  Cloud models can be useful when variable descriptions are complex or ambiguous.
  - How to verify: API key is configured and the **AI Configuration** connection test succeeds.
- **Azure OpenAI:** Best for enterprise compliance requirements
  -  Uses OpenAI models via your organization’s Azure deployment.
  -  Some organizations prefer Azure for governance controls (e.g., tenant-level access, data residency options).
  - How to verify: Your Azure endpoint/deployment details are configured and the **AI Configuration** connection test succeeds.

**Prompt Engineering Tips:**
1. **Be specific about context:** Include study domain in prompts
   -  Tell the model what kind of study it is (e.g., HIV cohort, maternal health survey) and what the dataset represents.
   -  “Age” in a clinical context may differ from “Age” in a survey; context reduces ambiguity.
   - How to verify: Review your prompts for domain-specific keywords and ensure they match your dataset.
2. **Provide examples:** Show format of good descriptions
   -  Give one or two example descriptions you consider correct.
   -  Examples teach the model the level of detail and style you want.
   - How to verify: Check that your examples are clear, concise, and consistent with your dataset.
3. **Set constraints:** Specify length limits (e.g., "in 2-3 sentences")
   -  Explicitly tell the model how long the output should be and what to include/exclude.
   -  Constraints make outputs consistent and easier to review.
   - How to verify: Review your prompts for length limits and ensure they match your needs.
4. **Request structured output:** Ask for specific elements (units, ranges)
   -  Ask the model to include specific fields (e.g., unit, population, timing) in a predictable pattern.
   -  Structured outputs are easier to QA and reuse.
   - How to verify: Review your prompts for specific elements and ensure they match your needs.

#### For Variable Matching

**Embedding Models:**
- **Ollama (nomic-embed-text):** Good for local semantic search
  -  Generates embeddings locally for recommendation similarity.
  -  Local embeddings can support privacy-sensitive workflows.
  - How to verify: Initialise completes successfully and recommendations are generated.
- **OpenAI (text-embedding-3-large):** Higher dimensional embeddings for better accuracy
  -  Uses a cloud embedding endpoint to represent variable text as vectors.
  -  Higher-capacity embedding models can improve recommendation quality when terminology varies.
  - How to verify: Initialise completes without embedding API errors/timeouts.
- **Azure OpenAI:** Enterprise-grade with data residency controls
  -  Uses your Azure deployment for embeddings.
  -  Helps align embedding generation with organizational governance.
  - How to verify: Initialise completes successfully using your Azure configuration.

### 6.2 Performance Optimization

#### Timeout Settings

Adjust timeouts based on:
- Model complexity
  -  Larger models often take longer per request.
  - How to verify: Increase timeout if requests fail intermittently; decrease if you need faster feedback.
- Network speed
  -  Cloud providers depend on internet connectivity and latency.
  - How to verify: If you see frequent timeouts, try 60 seconds and/or reduce batch sizes.
- Dataset size
  -  More variables means more AI calls; timeouts and batching have a bigger impact.
  - How to verify: Monitor system resources and adjust timeouts/batch sizes accordingly.

**Recommended Timeouts:**
- Local Ollama: 60-120 seconds
  -  Local machines vary; larger models may need longer timeouts.
  - How to verify: Increase timeout if requests fail intermittently; decrease if you need faster feedback.
- OpenAI API: 30-60 seconds
  -  Cloud APIs are usually fast, but network variability can still cause timeouts.
  - How to verify: If you see frequent timeouts, try 60 seconds and/or reduce batch sizes.
- Azure OpenAI: 60-120 seconds
  -  Enterprise gateways and network policies can add latency.
  - How to verify: If calls are reliable at 60 seconds, keep it; otherwise increase gradually.

#### Batch Processing

For large datasets (>500 variables):
1. Process in batches of 50-100 variables
   -  Split the workflow so you generate descriptions/embeddings in manageable chunks.
   -  Smaller batches reduce the impact of timeouts and make progress easier to resume.
   - How to verify: Monitor system resources and adjust batch sizes accordingly.
2. Monitor memory usage
   -  Watch system RAM/CPU usage during Initialise and mapping.
   -  Local models and large uploads can exceed available resources.
   - How to verify: Monitor system resources and adjust batch sizes accordingly.
3. Save progress frequently
   -  Download intermediate outputs or ensure output files are persisted before long runs.
   -  If a run fails mid-way, you can continue without restarting from zero.
   - How to verify: Check that intermediate outputs are saved correctly.
4. Schedule processing during off-peak hours
   -  Run large jobs when your machine and/or network is less busy.
   -  This can reduce timeouts and contention on shared infrastructure.
   - How to verify: Schedule jobs during off-peak hours and monitor system resources.

### 6.3 Cost Management

#### For Cloud Providers

**OpenAI Cost Estimation:**
- Description generation: ~$0.01 per variable (GPT-4)
  - Note: This is an approximate estimate and will vary by model, prompt length, and provider pricing.
  - How to verify: Review your OpenAI usage and estimate costs based on your specific usage.
- Embedding: ~$0.0001 per variable
  - Note: Embedding cost depends on the embedding model and total text length.
  - How to verify: Review your OpenAI usage and estimate costs based on your specific usage.
- Typical project: 200 variables = ~$2.02
  - Note: Total cost depends on retries, re-runs of Initialise, and how much context you upload.
  - How to verify: Review your OpenAI usage and estimate costs based on your specific usage.

**Cost Optimization Strategies:**
1. Use Ollama for initial exploration (free)
   -  Use local AI while you validate uploads, prompts, and workflow end-to-end.
   -  You can validate your workflow without incurring API costs.
   - How to verify: Use Ollama for initial exploration and estimate costs for cloud providers.
2. Switch to cloud for final production mappings
   -  Use a cloud provider for the final run when policies allow and you need higher accuracy.
   -  Cloud models can be more accurate, which can reduce manual review time (where governance allows).
   - How to verify: Compare a small pilot batch (e.g., 20 variables) across providers and confirm reviewer effort decreases.
3. Cache embeddings to avoid recomputation
   -  Avoid re-running Initialise unless inputs/models changed significantly.
   -  Re-running Initialise repeatedly can otherwise repeat the same embedding work.
   - How to verify: Re-open the project and confirm recommendations load without re-generating embeddings.
4. Use smaller models for simple datasets
   -  Choose a smaller chat/embedding model when terminology is straightforward.
   -  Smaller models may be faster and cheaper while still being “good enough” for straightforward codebooks.
   - How to verify: Compare outputs on a small sample and confirm quality remains acceptable.

---

## 7. Security and Privacy

### 7.1 Data Protection Principles

**For Health Data (PHI/PII):**

1. **Always use local Ollama** for initial processing
   -  The AI runs on your machine, and data does not need to be sent to a third party.
   -  This reduces privacy risk and simplifies governance approvals.
   - How to verify: AI provider is set to Ollama and the Base URL points to your local Ollama service.
2. **Remove identifiers** before using cloud providers
   -  Cloud AI should only receive de-identified metadata/example data that your governance permits.
   -  Cloud providers are external services; identifiers increase re-identification risk.
   - How to verify: Review uploaded files to confirm they do not contain names, IDs, phone numbers, addresses, or free-text identifiers.
3. **Use secure connections** (HTTPS) for all uploads
   -  Use secure network settings and approved deployment configurations when the tool is hosted centrally.
   -  Encryption in transit reduces the risk of interception.
   - How to verify: The tool URL begins with `https://` (for hosted deployments).
4. **Implement access controls** at organizational level
   -  Limit who can access the tool and the project folders containing `input/`, `results/`, and `logs/`.
   -  Access controls prevent accidental sharing and unauthorized use.
   - How to verify: Only approved users can access the tool and storage locations.
5. **Audit all data access** and maintain logs
   -  Keep records of who performed mappings and when, for review and accountability.
   -  Auditability supports governance and incident response.
   - How to verify: Mapping decisions and outputs can be traced to a user/date and stored in your project records.

### 7.2 Sensitive Data Handling

#### Before Upload

Run this checklist:
- [ ] Direct identifiers removed (names, IDs, addresses)
  -  Remove fields that directly identify a participant (e.g., name, national ID, phone number, exact address).
  -  Direct identifiers should not be uploaded to any tool used for mapping, especially when using cloud AI.
  - How to verify: Scan column names and a few sample rows for obvious identifiers.
- [ ] Dates shifted or aggregated (except year)
  -  Replace exact dates (e.g., birthdate, visit date) with safer forms (e.g., year only, or shifted dates) where possible.
  -  Exact dates can be identifying when combined with other data.
  - How to verify: Confirm you are not uploading full DOBs or exact event dates unless your governance allows it.
- [ ] Rare values flagged or generalized
  -  Identify unusual combinations (e.g., very rare diagnoses, rare locations) and generalize where needed.
  -  Rare values can re-identify individuals even when names are removed.
  - How to verify: Check for small counts (e.g., unique categories occurring <5 times) in the example data.
- [ ] Free-text fields reviewed for inadvertent identifiers
  -  Review narrative text fields (notes, comments) that may contain names, phone numbers, facilities, etc.
  -  Free text is high risk for accidental disclosure.
  - How to verify: If free text is not needed for mapping, exclude it; otherwise redact identifiers before upload.
- [ ] Small cell sizes (<5) suppressed
  -  Avoid uploading example data where a sensitive category/combination appears in very small numbers.
  -  Small cells increase re-identification risk.
  - How to verify: Aggregate or remove rare categories in the example data sample.

#### Data Minimization

Only upload:
- Variable names and descriptions (metadata)
  - Why: This is usually sufficient for mapping and is lower risk than full participant-level data.
- Representative example data (de-identified)
  - Why: Example values help validate mappings and transformations.
- Minimum necessary for mapping task
  - Why: Minimising data reduces privacy risk and makes approvals easier.

**Do NOT upload:**
- Complete datasets with sensitive information
  - Why: The tool is intended for harmonisation using metadata and small samples, not full sensitive datasets.
- Identifiable participant data
  - Why: Direct identifiers should never be used for mapping.
- Proprietary institutional information
  - Why: Keep internal operational details out of uploaded documents unless explicitly approved.

### 7.3 Compliance Considerations

#### For African Health Research

Ensure compliance with:
- **National data protection laws** (e.g., Kenya Data Protection Act, POPIA in South Africa)
  -  Legal requirements may restrict what data can be uploaded and which providers can be used.
  - How to verify: Your project has an identified applicable law/policy and a documented compliance approach.
- **Ethics committee requirements**
  -  Ethics approvals often specify what data handling is allowed.
  - How to verify: Your ethics approval/waiver explicitly covers the planned processing.
- **Institutional policies**
  -  Institutions may require specific hosting, access controls, or vendor approvals.
  - How to verify: IT/data governance has approved the deployment approach.
- **Funder requirements** (NIH, Wellcome Trust, etc.)
  -  Funders may impose data-sharing, security, or reporting constraints.
  - How to verify: You have checked the relevant funder policy and documented any obligations.

#### Documentation Requirements

Maintain records of:
- Data processing activities (GDPR Article 30)
  -  Records support audits and accountability for sensitive data handling.
  - How to verify: A processing record exists (even a simple spreadsheet) describing purpose, data types, and access.
- Informed consent for secondary use
  -  Consent may limit how data can be reused and shared.
  - How to verify: Consent language has been reviewed for harmonisation/secondary analysis.
- Data sharing agreements between institutions
  -  DSAs clarify allowed transfers, responsibilities, and security controls.
  - How to verify: A signed agreement exists for each sharing relationship.
- Security incident reports
  -  Incident logs support continuous improvement and required reporting.
  - How to verify: There is a defined process and contact for reporting incidents.

---

## 8. Collaboration and Governance

### 8.1 Communication Guidelines

#### For Mapping Questions

Use this escalation path:
1. Check documentation and FAQ
   -  Validate whether the question is already answered in guidance.
   -  This is the fastest way to resolve common questions and keeps communication channels usable.
   - How to verify: You can point to a specific section/link that addresses the question.
2. Consult with local data manager
   -  Ask someone familiar with your local dataset and coding conventions.
   -  Local context (site-specific coding) is often the missing piece.
   - How to verify: You have a documented recommendation or decision from the local reviewer.
3. Post to consortium Slack/Teams channel
   -  Ask the broader community when the issue affects multiple sites.
   -  Others may have solved the same mapping issue already.
   - How to verify: The thread includes enough context (variable name, description, example values, target candidate) for others to respond.
4. Raise issue in GitHub repository
   -  Log a formal issue for tracking and technical follow-up.
   -  GitHub issues create an auditable record and allow maintainers to prioritize fixes.
   - How to verify: The issue includes steps to reproduce and any error messages/logs.
5. Escalate to codebook owner
   -  Request an authoritative decision when a mapping affects shared definitions.
   -  The codebook owner ensures consistency across the consortium.
   - How to verify: A final decision and rationale are recorded.

#### For Technical Issues

1. Check troubleshooting guide (Section 10)
   -  Identify whether the issue matches a known symptom and recommended fix.
   -  Most technical failures are configuration or connectivity issues with standard fixes.
   - How to verify: You tried at least one suggested fix and noted what changed.
2. Review GitHub issues for similar problems
   -  Search for the same symptom/error message in existing issues.
   -  There may already be a known workaround or a fix in progress.
   - How to verify: You can link to an existing issue that matches your problem.
3. Contact technical support with:
   -  Provide enough detail for someone else to reproduce the issue.
   -  Incomplete reports slow down debugging and back-and-forth.
   - How to verify: Your message includes the items below and avoids sharing sensitive data.
   - Clear description of issue
   - Steps to reproduce
   - Error messages/logs
   - System information

---
## 9. Quality Assurance

### 9.1 Validation Steps

#### Level 1: Automated Checks

The tool performs:
- Data type compatibility checks
  -  Flags cases where a mapping is likely invalid (e.g., mapping a text field to a numeric target).
- Value range validation
  -  Highlights values that look impossible or inconsistent with expected units.
- Missing value pattern detection
  -  Summarises how often values are missing, which can reveal data quality issues.
- Duplicate mapping identification
  -  Detects when multiple study variables map to the same target (often a mistake unless intended).

#### Level 2: Peer Review

For critical variables:
1. Independent review by second data manager
   -  A second person checks the mapping choice without being influenced by the first decision.
   -  Independent review catches systematic interpretation errors.
   - How to verify: The reviewer’s name/date and outcome are recorded.
2. Discussion of uncertain mappings
   -  Ambiguous variables are discussed until the team agrees on a best interpretation.
   -  This reduces inconsistent handling across sites.
   - How to verify: The rationale is written in the mapping decision log.
3. Consensus decision documented
   -  The final decision is recorded so future mappers follow the same approach.
   -  Documentation supports reproducibility and audit.
   - How to verify: The mapping decision log includes the source variable, target variable, and rationale.

#### Level 3: Statistical Validation

After mapping:
1. Compare distributions (source vs. target)
   -  Check whether values “look similar” after transformation (e.g., age ranges, typical medians).
   -  Large shifts can indicate wrong units, wrong mapping, or a broken transformation.
   - How to verify: Basic summary stats (min/max/mean) and histograms are plausible.
2. Check for unexpected patterns
   -  Look for sudden category explosions, spikes at sentinel values, or impossible values.
   -  These often indicate coding or missing-value handling issues.
   - How to verify: Review outliers and top category counts; confirm missing codes are handled as missing.
3. Validate transformation rules with test data
   -  Apply transformation rules to known examples and confirm outputs match expectations.
   -  A correct mapping with a wrong rule silently corrupts results.
   - How to verify: Test at least 3–5 rows per transformed variable including edge cases.
4. Cross-tabulate categorical mappings
   -  Compare original categories vs mapped categories to ensure recoding is correct.
   -  Categorical errors are common and can invert meaning (e.g., 1=Yes vs 1=No).
   - How to verify: A cross-tab table has no unexpected category shifts.

### 9.2 Quality Metrics

Track these indicators:

| Metric | Target | Action if Below Target |
|--------|--------|------------------------|
| **Mapping Completion Rate** | >95% | Investigate unmapped variables |
| **High-Confidence Mappings** | >80% | Review codebook clarity |
| **Transformation Success** | >98% | Debug transformation rules |
| **Reviewer Agreement** | >90% | Clarify ambiguous variables |

---

## 10. Troubleshooting Common Issues

### Quick symptom guide

| Symptom | Likely cause | What to try |
|---|---|---|
| **"Cannot connect" in AI Configuration** | Ollama not running, wrong Base URL, or no models pulled yet | Verify Ollama is running; check Base URL; ensure models are available (e.g., `llama3.1:8b`, `nomic-embed-text`) |
| **"No recommendations available" / mapping page says not initialised** | Initialise step not run, or recommendation files not created | Go to **Initialise** and run the Recommendation Engine |
| **No example preview / Transform Mode not useful** | No `example_data.csv`, or column headers don’t match `variable_name` | Upload example data and ensure headers match exactly |
| **AI requests time out** | Timeout too low for your model/machine | Increase timeout to 60–120 seconds |

### 10.1 Connection Problems

#### Issue: "Cannot connect to Ollama"

**Symptoms:** Error message when testing AI connection

**Solutions:**
1. Check if Ollama is running: `docker ps` or check Ollama app
   -  Confirm the Ollama service is running and reachable.
   -  The tool cannot call Ollama if the service is stopped.
   - How to verify: `http://localhost:11434/api/tags` responds (or the equivalent host in Docker).
2. Verify URL in .env file:
   -  Ensure the configured base URL matches how Ollama is running (local vs Docker).
   -  A wrong base URL is a common cause of connection failures.
   - How to verify: The base URL shown in **AI Configuration** matches your deployment mode.
   - Docker: `http://ollama:11434`
   - Local: `http://localhost:11434`
3. Test connection manually: `curl http://localhost:11434/api/tags`
   -  Call the Ollama API directly to distinguish app issues from Ollama issues.
   -  Manual checks narrow down the root cause faster.
   - How to verify: The command returns a JSON response listing models.
4. Check firewall settings
   -  Confirm your firewall/network allows connections to the Ollama port.
   -  Firewalls can block localhost-to-app or container-to-host connections.
   - How to verify: Temporarily allow port 11434 and re-test connection.

#### Issue: "API timeout"

**Symptoms:** Requests hang or timeout

**Solutions:**
1. Increase timeout in AI Configuration (try 180 seconds)
   -  Give slow models more time to respond.
   -  Larger models (or slower machines) can exceed default timeouts.
   - How to verify: After increasing timeout, re-run the failing action and confirm it completes.
2. Check internet connection (for cloud providers)
   -  Ensure you have stable connectivity to the provider.
   -  Cloud calls fail if the network is unstable.
   - How to verify: Try a simple web request and confirm connectivity is stable.
3. Reduce batch size
   -  Run fewer variables per batch.
   -  Smaller batches reduce load and reduce the chance of timeouts.
   - How to verify: Re-run Initialise with a smaller subset and confirm completion.
4. Try different time of day (less server load)
   -  Avoid peak usage hours for shared cloud services.
   -  Provider-side congestion can increase latency.
   - How to verify: Repeat the same request later and compare reliability.

### 10.2 Mapping Quality Issues

#### Issue: "Low confidence scores across the board"

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Poor variable descriptions | Improve description quality, add context |
| Incompatible datasets | Verify codebook matches data domain |
| AI model not suitable | Try different embedding model |
| Lack of example data | Upload representative examples |

#### Issue: "Incorrect mappings suggested"

**Troubleshooting Steps:**
1. Review variable descriptions for clarity
   -  Improve ambiguous or overly short descriptions.
   -  Recommendations depend heavily on description quality.
   - How to verify: Updated descriptions mention units/coding and what the variable represents.
2. Check for terminology mismatches (e.g., UK vs. US terms)
   -  Ensure descriptions use consistent terminology with the target codebook.
   -  Different terms can reduce semantic similarity.
   - How to verify: Add synonyms or clarifying phrases and see if recommendations improve.
3. Verify example data is representative
   -  Ensure the sample shows real ranges and categories.
   -  Reviewers rely on example values to validate mappings.
   - How to verify: The sample includes typical and edge-case values.
4. Consider domain-specific AI fine-tuning
   -  If available, use a model/provider better suited to your domain.
   -  Some models handle medical terminology better than others.
   - How to verify: Compare recommendations on a small sample across models/providers.

### 10.3 Technical Errors

#### Issue: "Out of memory errors"

**Solutions:**
1. Process in smaller batches
   -  Reduce the number of variables processed at once.
   -  Smaller batches reduce memory pressure.
   - How to verify: The same workflow completes without memory errors on smaller batches.
2. Close other applications
   -  Free RAM/CPU on your machine.
   -  Local inference competes with other applications for resources.
   - How to verify: Memory usage decreases and the tool runs more reliably.
3. Increase Docker memory allocation
   -  Give Docker more RAM (especially on Windows/macOS).
   -  Containers can hit memory limits even when the host has free RAM.
   - How to verify: Docker settings show increased memory and the workflow completes.
4. Use smaller AI models
   -  Choose a lighter model that fits your hardware constraints.
   -  Smaller models reduce memory usage and latency.
   - How to verify: The selected model runs without OOM errors.

#### Issue: "Transformation rules failing"

**Debugging Process:**
1. Test rule with simple examples
   -  Apply the rule to known inputs and confirm the output.
   -  Simple tests catch obvious logic errors early.
   - How to verify: A small set of test inputs produce expected outputs.
2. Check for edge cases (nulls, zeros, outliers)
   -  Confirm the rule behaves correctly on missing/rare values.
   -  Edge cases often cause runtime errors or incorrect outputs.
   - How to verify: Nulls and sentinel values are handled as intended.
3. Verify syntax (Python for direct, dict for categorical)
   -  Ensure the transformation uses the correct allowed format.
   -  Syntax errors cause transformations to fail or produce wrong results.
   - How to verify: The tool accepts the rule without errors and produces expected preview outputs.
4. Review error messages carefully
   -  Use the exact error text to identify whether it is a parsing, data, or logic issue.
   -  The error message usually indicates the failing step.
   - How to verify: After adjusting the rule, the same operation runs without the previous error.

### 10.4 Getting Help

**Before Requesting Help:**
- [ ] Checked this guide
  -  You looked up the relevant troubleshooting section first.
  -  Many issues (timeouts, missing files, connection problems) have quick fixes already documented.
- [ ] Searched GitHub issues
  -  You searched for the same error message/symptom in the project issue tracker.
  -  You may find an existing workaround or confirmation that the issue is already known.
- [ ] Reviewed error logs
  -  You checked any visible error output (and, if available, relevant log files) to capture the exact message.
  -  The exact error text usually points to the real cause (e.g., missing file vs. AI connection vs. formatting).
- [ ] Tried basic troubleshooting steps
  -  You tried simple actions like reloading the app, re-running Initialise, or increasing timeout.
  -  These steps often resolve transient failures without needing escalation.

**When Requesting Help, Include:**
- Clear description of problem
- Steps to reproduce
- Error messages (full text)
- System information (OS, Docker version, etc.)
- Screenshots if relevant
- Anonymized example data if possible

**Support Channels:**
- GitHub Issues: Technical problems
- Consortium Slack: General questions
- Email: twinmugume@gmail.com

---

## 11. Appendix

### 11.1 Glossary

**Common Data Model (CDM):** A standardized structure for organizing health data

**Codebook:** A document defining variables, their meanings, and allowed values

**Embedding:** Vector representation of text for semantic similarity comparison

**Harmonisation:** Process of aligning data from multiple sources to a common structure

**Large Language Model (LLM):** AI system trained on text to understand and generate human language

**Metadata:** Data about data (e.g., variable names, descriptions, types)

**Ontology:** Formal representation of knowledge with defined relationships between concepts

**Semantic Similarity:** Measure of how similar two pieces of text are in meaning

**Transformation Rule:** Instructions for converting data from one format to another

### 11.2 Useful Standards and Resources

#### Health Data Standards

- **OMOP CDM:** [https://ohdsi.org/data-standardization/](https://ohdsi.org/data-standardization/)
- **FHIR:** [https://hl7.org/fhir/](https://hl7.org/fhir/)
- **CDISC:** [https://www.cdisc.org/standards](https://www.cdisc.org/standards)

#### Terminology Services

- **LOINC:** [https://loinc.org/](https://loinc.org/)
- **SNOMED CT:** [https://www.snomed.org/](https://www.snomed.org/)
- **ICD-11:** [https://www.who.int/standards/classifications/classification-of-diseases](https://www.who.int/standards/classifications/classification-of-diseases)

#### Training Resources

- **The Good Docs Project:** Templates and guides for technical documentation
- **OHDSI Tutorials:** Free courses on data standardization
- **eLwazi Platform:** DS-I Africa data sharing platform

### 11.3 Template Documents

#### Mapping Decision Log Template

```markdown
# Mapping Decision Log

**Project:** [Project Name]
**Date:** [YYYY-MM-DD]
**Mapper:** [Your Name]

## Variables Reviewed: [Start - End range]

| Source Variable | Target Variable | Decision | Confidence | Notes |
|----------------|----------------|----------|------------|--------|
| patient_age | age_years | Accept | 95% | Direct match |
| height | height_m | Accept with transform | 85% | Divide by 100 (cm to m) |
| sex_code | gender_text | Custom mapping | 70% | Recode: 1→Male, 2→Female |
| study_arm | - | No match | - | Study-specific variable, not in codebook |

## Unresolved Issues

1. Variable X has ambiguous description - need clarification from PI
2. Variable Y has unexpected values in example data - data quality issue?

## Next Steps

- [ ] Consult with PI on Variable X
  -  Ask the Principal Investigator (or study lead) what the variable represents and how it was collected/coded.
  -  Only the study team can resolve truly ambiguous variables.
- [ ] Investigate data quality for Variable Y
  -  Check whether the variable has unexpected values, missingness, or inconsistent coding.
  -  Data quality problems can make a correct mapping look “wrong” in example data.
- [ ] Review unmapped variables with team
  -  Confirm whether unmapped variables should remain unmapped, be added to the codebook, or be derived from other fields.
  -  Unmapped variables often represent important study-specific concepts that need a governance decision.

```

#### Quality Assurance Checklist

```markdown
# QA Checklist: Variable Mapping

**Project:** [Project Name]
**Reviewer:** [Your Name]
**Date:** [YYYY-MM-DD]

## Completeness
- [ ] All required variables mapped
  -  Every variable the consortium expects for analysis/reporting has a confirmed mapping (or a documented reason why not).
  - How to verify: Confirm no required variables are left “To do” or unmapped without rationale.
- [ ] Optional variables reviewed
  -  Optional variables were checked and either mapped (if useful) or consciously left unmapped.
  - How to verify: Ensure you can justify why each optional variable is or isn’t mapped.
- [ ] Unmapped variables documented with rationale
  -  For each unmapped variable you recorded why (e.g., not in codebook, poor quality, not relevant).
  - How to verify: Review the mapping decision log for a short reason per unmapped variable.

## Accuracy
- [ ] High-confidence mappings verified (spot check 10%)
  -  You manually verified a sample of “easy” mappings to ensure the tool is behaving as expected.
  - How to verify: Pick ~10% of high-confidence items and compare against documentation and example values.
- [ ] Low-confidence mappings reviewed (100%)
  -  You reviewed every low-confidence recommendation because these are higher risk.
  - How to verify: Ensure each low-confidence variable has a deliberate decision (mapped, custom mapped, or left unmapped).
- [ ] Transformation rules tested with example data
  -  Transformations produce valid outputs on real-looking rows (including missing values).
  - How to verify: Compare a few before/after examples and confirm units/categories match the target codebook.
- [ ] Edge cases handled (nulls, outliers)
  -  You decided what to do with missing codes, zeros, impossible values, and extreme outliers.
  - How to verify: Test transformations and validation checks on those edge-case rows.

## Documentation
- [ ] Mapping decisions logged
  -  Non-obvious mappings and decisions are written down with a short rationale.
  - How to verify: Confirm the mapping decision log is populated as you work, not only at the end.
- [ ] Assumptions documented
  -  Any assumptions you made (e.g., inferred unit, inferred coding) are recorded.
  - How to verify: Review notes for statements like “Assumed X means Y because…”.
- [ ] Questions raised and answered
  -  Any unresolved issues were escalated to the right person and you recorded the answer.
  - How to verify: Ensure each question has an owner and a final decision.
- [ ] Final mapping file exported
  -  You exported the final mapping results after review.
  - How to verify: Confirm the exported file is saved with a clear filename/version and is ready to share.

## Review
- [ ] Peer review completed
  -  A second person reviewed the mappings for common errors and conceptual mismatches.
  - How to verify: Record the reviewer name/date and any changes made after review.
- [ ] Domain expert consulted on uncertain mappings
  -  A clinician/epidemiologist/data steward reviewed variables where semantics are subtle.
  - How to verify: Note which variables were reviewed and what decision was reached.
- [ ] Statistical validation performed
  -  After applying mappings/transformations, you checked distributions and obvious inconsistencies.
  - How to verify: Compare summary statistics and category frequencies before/after transformation.
- [ ] Discrepancies resolved
  -  Any mismatches discovered during review/validation were corrected or documented.
  - How to verify: There are no outstanding “known issues” without an owner/plan.

**Sign-off:**
Mapper: _________________ Date: _________
Reviewer: _______________ Date: _________
```

### 11.4 FAQs

**Q: How long does typical mapping project take?**
A: For a dataset with 200 variables, expect 4-8 hours total: 1-2 hours setup, 2-4 hours AI-assisted mapping, 1-2 hours review and QA.

**Q: Can I map multiple datasets simultaneously?**
A: Yes, the tool supports multiple studies. However, focus on one at a time for quality.

**Q: What if my variable doesn't fit any codebook variable?**
A: Document it as unmapped, discuss with consortium, potentially propose codebook addition.

**Q: How do I update mappings after initial submission?**
A: Re-upload the study, make corrections, and export updated mapping file. Keep version history.

**Q: Can I use this tool for non-health data?**
A: Yes! The principles apply to any data harmonisation task. Adjust codebook and terminology accordingly.

**Q: Is my data secure?**
A: When using local Ollama, data never leaves your machine. For cloud providers, remove all identifiers first.

**Q: How often is the tool updated?**
A: Check GitHub releases page for updates. Major updates quarterly, bug fixes as needed.

**Q: Can I contribute improvements?**
A: Yes! Submit issues and pull requests on GitHub. See CONTRIBUTING.md for guidelines.

---

*This guide is licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)*