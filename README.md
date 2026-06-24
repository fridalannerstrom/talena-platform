# **Talena**
### *Talent assessment, reimagined.*

Talena is a modern assessment platform built by **TQ AI Nordic**, designed to replace outdated workflows in legacy testing systems.  
In the MVP version, Talena becomes the **main hub** where TQ and customers:

- create recruitment projects  
- add candidates  
- send out psychometric tests  
- follow test status and results  

Sova acts as the **test engine in the background**, integrated via their standard API.

Talena provides a clean, intuitive UI and a future-proof architecture that makes psychometric testing simple, fast, and scalable.

---

## Key Strengths: assessment-based insight logic

The **Key Strengths** section is designed to identify a small number of clearly supported strength themes from a candidate’s assessment results.

The purpose is not to label every high score as a strength. Instead, the system groups selected assessment indicators into broader behavioural themes and only displays a theme when the available evidence meets defined rules.

This is currently a deterministic, rule-based implementation. The rules are transparent and can be reviewed, adjusted and validated by behavioural scientists and psychometric specialists.

---

### 1. Data sources

The Key Strengths logic can currently use results from:

- Personality assessments
- Motivation assessments
- Cognitive ability assessments

However, a Key Strength must currently be anchored in personality data.

This means:

- Personality only: Key Strengths can be generated
- Personality and motivation: Key Strengths can be generated
- Personality and cognitive ability: Key Strengths can be generated
- Personality, motivation and cognitive ability: Key Strengths can be generated
- Motivation only: the Key Strengths section is not shown
- Cognitive ability only: the Key Strengths section is not shown
- Motivation and cognitive ability without personality: the Key Strengths section is not shown

The reason for this is that the section describes broader behavioural tendencies. Motivation results primarily describe drivers and preferences, while cognitive ability results describe specific capacities. These results may support or add context to a strength theme, but they are not currently used as the sole basis for a broader behavioural strength.

---

### 2. Score normalisation

The different assessment types use different score formats.

The system therefore stores both:

- the original score
- a normalised internal score

The normalised score is used only for comparison and rule evaluation. The original score and scale are retained for display.

Examples:

| Assessment source | Original display | Internal comparison |
|---|---:|---:|
| Personality | STEN 8 of 10 | 8.0 |
| Motivation | Original motivation scale | Converted internally |
| Cognitive ability | 82nd percentile | 8.2 |

The normalised score is not presented as a new psychometric score. It is only used internally to apply consistent thresholds across assessment types.

---

### 3. Behavioural themes

Individual indicators are grouped into broader themes through a controlled theme catalogue.

Example:

```python
"strategic_complex_thinking": {
    "title": "Strategic and complex thinking",
    "indicator_keys": {
        "strategic thinking",
        "strategic insight",
        "strategic focus",
        "complex thinking",
        "conceptual",
        "architect",
        "creates the vision",
    },
}
```

A theme may therefore be supported by one or several related indicators.

Examples of current themes include:

- Structured and reliable delivery
- Analytical problem solving
- Strategic and complex thinking
- Innovation and original thinking
- Learning orientation
- Network building
- Collaborative working style
- Supporting and developing others
- Adaptability under pressure
- Drive and ownership
- Leadership and influence
- Communication and engagement
- Integrity and sincerity
- Energy and momentum

The theme catalogue is intentionally explicit rather than generated freely by AI. This makes it possible to review:

- which indicators belong to each theme
- whether the indicators are conceptually related
- whether the theme title is justified
- whether the interpretation is appropriately cautious

---

### 4. Threshold for a Key Strength

Only clearly elevated personality indicators may support a Key Strength.

The current default threshold is:

```text
Normalised score >= 7
```

A theme is displayed when either:

1. at least two elevated personality indicators support the theme, or
2. one particularly elevated personality indicator reaches the theme’s single-indicator threshold

The default single-indicator threshold is:

```text
Normalised score >= 8
```

Each theme may define its own thresholds:

```python
"minimum_strong": 2,
"allow_single_from": 8,
```

This means a specific theme can be configured to require more supporting evidence if needed.

---

### 5. Personality anchoring

A Key Strength must currently include at least one elevated personality result.

Cognitive and motivation results may later be used to strengthen, qualify or prioritise a theme, but they should not independently create a broad behavioural strength.

For example:

```text
Strategic Thinking: STEN 7
Complex Thinking: STEN 8
Logical Reasoning: 84th percentile
```

may support a theme such as:

```text
Strategic and complex thinking
```

However, two high cognitive ability scores without personality support would not currently generate this behavioural theme.

Cognitive ability results should instead remain visible in the dedicated ability-results section.

---

### 6. Double-edged indicators

Some indicators may be highly significant without representing an uncomplicated strength.

Examples include:

- Stubborn
- Rigid
- Casual
- Dramatic
- Unpredictable
- Dependence
- Vulnerability
- Volatility
- Impulsiveness

These indicators are stored in a controlled exclusion list:

```python
DOUBLE_EDGED_INDICATORS = {
    "stubborn",
    "rigid",
    "casual",
    "dramatic",
    "unpredictable",
    "dependence",
    "vulnerability",
    "volatility",
    "impulsiveness",
}
```

A high score on one of these indicators does not automatically create a Key Strength.

For example:

```text
Stubborn: STEN 10
```

is highly important, but it may indicate different things depending on the wider profile:

- persistence
- conviction
- resistance to influence
- difficulty adapting
- unwillingness to reconsider a position

The result should therefore be interpreted together with related indicators.

A combination such as:

```text
Stubborn: STEN 10
Flexibility: STEN 2
Adaptability: STEN 2
Adapting to Change: STEN 1
```

would be more appropriate for an **Area to Explore** than an automatic Key Strength.

---

### 7. Supporting indicators

Every displayed Key Strength includes the assessment indicators that supported it.

Example:

```text
Strategic and complex thinking

Supporting indicators:
- Complex Thinking: STEN 8
- Strategic Thinking: STEN 7
- Learning Mindset: STEN 7
```

This allows the user to see:

- which results contributed to the theme
- which assessment produced each result
- the original score and scale
- why the theme was selected

The aim is to avoid opaque statements where the platform presents a conclusion without showing its evidence.

---

### 8. Combined visual level

Each theme receives a combined visual level based on the average of its supporting indicators.

Example:

```text
Complex Thinking: 8
Strategic Thinking: 7
Learning Mindset: 7
```

Combined level:

```text
7.3
```

Rounded display:

```text
7/10
```

This level is a UI summary. It is not:

- a new psychometric scale
- a validated composite score
- an official assessment result
- a substitute for the original scores

The interface should clearly communicate that the level is a visual summary of supporting evidence.

---

### 9. Maximum number of themes

The system currently displays a maximum of four Key Strengths.

Themes are sorted primarily by:

1. combined evidence level
2. number of supporting indicators

This prevents the report from becoming overloaded and keeps the focus on the most strongly supported themes.

---

### 10. Duplicate indicators

Some assessment data may contain repeated indicator names.

The current implementation removes exact duplicate names during normalisation.

This avoids accidentally counting the same indicator multiple times.

However, some repeated names may represent:

- different report constructs
- different competency frameworks
- different source scales
- related but not identical interpretations

This area requires further review. A future implementation may need stable indicator IDs rather than relying only on indicator names.

---

### 11. Interpretation principles

The Key Strengths section follows these principles:

1. A high score is not automatically a strength.
2. A strength should be supported by conceptually related indicators.
3. Personality data should anchor broad behavioural interpretations.
4. Motivation describes drivers and preferences, not necessarily capability.
5. Cognitive results describe ability, not a complete behavioural tendency.
6. Double-edged indicators require contextual interpretation.
7. Original scores and scales should remain visible.
8. Combined levels must not be presented as validated psychometric scores.
9. Themes should be phrased probabilistically, not as fixed truths.
10. Results should support professional judgement, not replace it.

Preferred wording includes:

- “may indicate”
- “may be comfortable with”
- “may show”
- “could contribute to”
- “may be relevant where”

Avoid wording such as:

- “the candidate is”
- “the candidate will”
- “this proves”
- “this guarantees”
- “the candidate lacks”

---

### 12. Current limitations

The current implementation is an early rule-based version.

Known limitations include:

- Theme mappings have not yet been formally validated.
- Thresholds are configurable but not yet empirically calibrated.
- Some indicators may reasonably belong to more than one theme.
- Similar themes may be generated from overlapping indicators.
- Duplicate indicator names may require more advanced handling.
- The meaning of high and low scores may differ between constructs.
- Some constructs are bipolar or context-dependent.
- The current combined level is descriptive, not psychometrically validated.
- Process context does not yet fully affect theme selection or prioritisation.
- Motivation and cognitive results are not yet deeply integrated into the strength rules.
- Cultural, language and norm-group considerations are not yet included in the interpretation logic.

---

### 13. Areas for psychometric review

Behavioural scientists and psychometric specialists are invited to review:

#### Theme validity

- Do the indicators within each theme measure sufficiently related constructs?
- Are any themes too broad?
- Are any theme titles more confident than the evidence supports?

#### Thresholds

- Is STEN 7 an appropriate threshold for elevated evidence?
- Should a single STEN 8 result be sufficient for specific themes?
- Should some themes require at least two or three indicators?
- Should cognitive percentiles use different thresholds?

#### Direction of interpretation

- Which indicators are positive when high?
- Which are potentially problematic when high?
- Which require mid-range interpretation?
- Which are genuinely bipolar?
- Which should never be interpreted independently?

#### Overlap

- Can the same indicator reasonably support several themes?
- Should one indicator be allowed to appear in multiple Key Strengths?
- Should similar themes be merged when they use overlapping evidence?

#### Language

- Are the behavioural descriptions appropriately cautious?
- Do they distinguish preference, behaviour, capacity and motivation?
- Are any phrases likely to overstate predictive validity?

#### Evidence rules

- Should personality always be required?
- Can cognitive ability independently support a narrowly defined strength?
- How should motivation results contribute?
- Should test combinations affect confidence levels?

---

### 14. Future development

Planned improvements may include:

- psychometrically reviewed theme mappings
- indicator metadata using stable IDs
- construct-specific thresholds
- explicit positive, negative and double-edged direction rules
- combination rules across related indicators
- contradiction detection
- prevention of excessive theme overlap
- role-context prioritisation
- confidence ratings
- separate cognitive-strength and motivational-driver sections
- validated wording libraries
- automated tests for known assessment profiles
- versioning of interpretation rules

---

### 15. Important disclaimer

The Key Strengths section is intended as decision support.

It should not be used as:

- a standalone selection decision
- a diagnosis
- a definitive description of an individual
- a replacement for trained interpretation
- a substitute for interviews, references or other relevant evidence

Assessment results should always be interpreted in context and together with other available information.


---

# ⭐ **MVP Scope**

The primary goal of the MVP:

> **Make Talena the platform where all test-related work happens — not Sova.**  
> Sova should only be used as a backend test processor.

No customer or consultant should ever need to log into Sova again.

---

# 🎯 **Core MVP Features**

## **1. Authentication & User Management**

### **TQ Admin**
- Full access to all customers, projects, and candidates
- Create and manage customer accounts
- Create recruitment projects on behalf of customers
- Configure test templates mapped to Sova projects (optional in MVP)

### **Customer User**
- Secure login to Talena
- Access only to their own projects and candidates
- Create recruitment projects
- Add candidates
- View test status and results

### **Candidate (no login)**
- Receives test link via Sova
- Completes assessment in Sova platform
- No Talena login needed in MVP

---

# 🧩 **Concepts & Mapping**

Talena and Sova handle different responsibilities:

### **Talena**
- Users (TQ + Customers)
- Recruitment projects
- Candidates
- Test templates (mapped to Sova)
- Test status & result display
- Permissions and access control

### **Sova**
- Test execution engine
- Test packages (projects)
- Sending test invitations (MVP)
- Callbacks for status & results

**Talena controls who sees what.  
Sova stores test data, but knows nothing about customers, projects or permissions.**

### **Key Integrations in MVP**
- Use a single **TQ Sova account**  
- Use **pre-created Sova projects** (test packages)  
- For each candidate:
  1. Talena sends an order to Sova (`order-assessment`)  
  2. Sova sends invitation email to candidate  
  3. Sova sends callbacks to Talena on status updates  
  4. Talena displays test progress and result links  

---

# 🚀 **MVP Functionality Overview**

## **Projects**
Users can:
- Create recruitment projects
- Select a test template (mapped to a Sova project)
- See a list of all their active projects

## **Candidates**
Users can:
- Add candidates to a project
- Automatically send test invitations via Sova
- Track candidate status:
  - Invitation sent  
  - In progress  
  - Completed  
- View result report link when available

Talena stores the **request_id** from Sova to handle callbacks and match test data to candidates.

---

# 🔌 **Sova Integration (MVP)**

### Required Sova API calls:
- `POST /order-assessment/{project_code}`  
  Send test order for a candidate

- Callback: **Status updates**  
  Used to update candidate's test progress

- Callback: **Results available**  
  Provides PDF report link or raw score data

### MVP Decision:
📌 **Email invitations will be sent by Sova**  
Later versions may replace this with Talena-branded emails.

---

# 🏗️ **Technical Setup (MVP)**

- **Backend:** Django (Python)
- **Frontend:** HTML / Django templates (MVP)
- **Database:** PostgreSQL (Azure)
- **Hosting:** Azure App Service
- **Storage:** Azure Blob Storage (for future uploads)
- **CI/CD:** GitHub Actions (optional in MVP)
- **Environments:**  
  - `dev`  
  - `production`

---

# Talena – System Architecture Overview

This document outlines how Talena is structured across GitHub, Azure, and Django. The goal is to create a scalable, maintainable, and production‑ready foundation for the platform.

---

## 1. Environments

Talena uses separate environments for clarity, stability, and security.

| Environment | Purpose |
|------------|----------|
| **Local** | Development on your own machine |
| **Dev** | Internal development & feature testing |
| **Stage** | Stable testing environment before release |
| **Prod** | Live production |

Each environment has its own Azure resources (App Service, database, storage, logging).

---

## 2. Azure Structure & Naming Conventions

Talena follows consistent naming for all Azure resources.

**Resource Groups**
- `rg-talena-dev`
- `rg-talena-stage`
- `rg-talena-prod`

**App Services**
- `app-talena-dev`
- `app-talena-stage`
- `app-talena-prod`

**App Service Plans**
- `plan-talena-dev`
- `plan-talena-stage`
- `plan-talena-prod`

**PostgreSQL Databases**
- `pg-talena-dev`
- `pg-talena-stage`
- `pg-talena-prod`

**Blob Storage Accounts**
- `sttalenadev`
- `sttalenastage`
- `sttalenaprod`

All environments keep their own separate configuration, database, and storage.

---

## 3. Repository Structure

```
talena/
│
├── backend/            # Django project
│   ├── talena/         # settings, urls, wsgi
│   ├── apps/           # modular Django apps
│   └── manage.py
│
├── infra/              # Infrastructure-as-Code (optional)
│
├── docs/               # Documentation
│   └── ARCHITECTURE.md
│
├── .github/
│   └── workflows/      # CI/CD pipelines
│
└── README.md
```

---

## 4. Django Settings Structure

Talena uses environment-based settings:

```
backend/
  talena/
    settings/
      base.py
      dev.py
      stage.py
      prod.py
```

- `base.py`: shared core settings  
- `dev.py`, `stage.py`, `prod.py`: environment overrides  
- Active environment controlled via `DJANGO_SETTINGS_MODULE`

---

## 5. Branch Strategy

Talena follows a simple branching model:

- `main` – production-ready code  
- `develop` – active development branch  

**Feature branches:**
```
feature/<feature-name>
```

**Hotfix branches:**


```
hotfix/<bug-name>
```

Pull requests go into `develop`, which is merged into `main` before release.



-----


# 🧪 **What is *not* included in MVP**

To stay focused and deliver fast, the following are **intentionally out of scope**:

- AI features (summaries, interpretation, matching, etc.)
- Branded test invitation emails
- PDF generation inside Talena
- Advanced dashboards or analytics
- Multi-language support
- Mobile-optimized UI
- Candidate portal
- Multi-admin customer roles
- Custom Sova project creation via API

These can be added after the MVP foundation is stable.

---

# 🛣️ **Future Roadmap (Beyond MVP)**

- AI-powered candidate summaries  
- AI-driven test interpretation  
- Candidate comparison & match scoring  
- Fully branded Talena email templates  
- Customer self-service portal  
- Custom test workflows  
- PDF report generator  
- Integrations with ATS systems  

---

# 📬 **Support / Contact**
Developed by **TQ AI Nordic**  
For integration questions or access to Sova test environments:  
support@sovaassessment.com (external)  
support@tqnordic.com (internal)

---

# ✔️ **Summary**

Talena MVP delivers:

- A clean recruitment-centric interface
- A unified flow for managing projects and candidates
- Seamless integration with Sova
- A foundation for future AI-enhanced features

Talena becomes the **front-end experience**.  
Sova becomes the **engine**.  
Users see only Talena — never Sova.

