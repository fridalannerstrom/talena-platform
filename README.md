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

## Areas to Explore: assessment-based insight logic

The **Areas to Explore** section is designed to identify assessment patterns that may benefit from further investigation in an interview, feedback conversation or development discussion.

The purpose is not to label weaknesses or make fixed conclusions about a candidate. Instead, the system highlights combinations of results that may warrant follow-up and presents them as hypotheses to verify.

The current implementation is deterministic and rule-based. All rules, thresholds and theme mappings can be reviewed and adjusted by behavioural scientists and psychometric specialists.

---

### 1. Purpose of the section

Areas to Explore are intended to help users answer questions such as:

- Which assessment patterns may require additional context?
- Which topics should be explored through behavioural interview questions?
- Where might a candidate use compensating strategies?
- Which results should not be interpreted in isolation?
- Which patterns may be relevant to role fit, onboarding or development?

An Area to Explore is not:

- a confirmed weakness
- a diagnosis
- a prediction of failure
- a standalone selection decision
- a substitute for trained interpretation

The wording should remain cautious and exploratory.

Preferred phrases include:

- “may be useful to explore”
- “could indicate”
- “may require further context”
- “should be verified through examples”
- “may become more demanding in some situations”

---

### 2. Data source

The current Areas to Explore logic is anchored in personality assessment data.

Personality results are used because the section describes broader behavioural tendencies and possible risk patterns.

The current behaviour is:

- Personality only: Areas to Explore can be generated
- Personality and motivation: Areas to Explore can be generated
- Personality and cognitive ability: Areas to Explore can be generated
- Personality, motivation and cognitive ability: Areas to Explore can be generated
- Motivation only: the section is not shown
- Cognitive ability only: the section is not shown
- Motivation and cognitive ability without personality: the section is not shown

Motivation and cognitive results may later be used to add context, but they do not currently create Areas to Explore independently.

---

### 3. Two types of exploration logic

The system currently creates Areas to Explore in two ways:

1. **Combination rules**
2. **Low-score theme rules**

These two approaches capture different kinds of evidence.

---

## 4. Combination rules

Combination rules identify patterns where:

- one or more double-edged indicators are clearly elevated, and
- one or more related indicators are clearly low

This allows the system to interpret a result in context rather than treating a single high score as automatically positive or negative.

Example:

```text
Stubborn: STEN 10
Flexibility: STEN 2
Adaptability: STEN 2
Adapting to Change: STEN 1
```

This combination may create:

```text
Flexibility when challenged
```

The interpretation is not that the candidate is “bad” or “inflexible”. The pattern suggests that strong persistence or conviction may sometimes make it harder to reconsider a position or change direction quickly.

---

### 4.1 Structure of a combination rule

A combination rule contains:

```python
"flexibility_when_challenged": {
    "title": "Flexibility when challenged",
    "high_any": {
        "stubborn",
        "rigid",
    },
    "low_any": {
        "flexibility",
        "adaptability",
        "adapting to change",
        "openness to change",
    },
    "high_threshold": 8,
    "low_threshold": 4,
}
```

The rule is triggered when:

- at least one indicator in `high_any` reaches the high threshold, and
- at least one indicator in `low_any` reaches the low threshold

The default interpretation principle is:

```text
high double-edged indicator + related low indicator = topic to explore
```

---

### 4.2 Current combination themes

Current examples include:

- Flexibility when challenged
- Structure and follow-through
- Independent decision-making
- Emotional response under pressure

These rules may use patterns such as:

```text
Stubborn high + Flexibility low
Casual high + Self-Discipline low
Dependence high + Independence low
Vulnerability high + Emotional Control low
```

---

### 5. Low-score theme rules

The system also identifies Areas to Explore when several related personality indicators are clearly low.

Example:

```text
Analysing Problems: STEN 1
Analyst: STEN 2
Using the Facts: STEN 2
Analytical Thinking: STEN 3
```

This may create:

```text
Analytical problem solving
```

The result does not prove that the candidate lacks analytical ability. It indicates that the personality assessment provides a pattern worth exploring through examples and other evidence.

---

### 5.1 Thresholds for low-score themes

The current default threshold is:

```text
Normalised score <= 4
```

A theme is displayed when either:

1. at least two related indicators are low, or
2. one indicator is extremely low

The current extremely low threshold is:

```text
Normalised score <= 2
```

This allows both broader patterns and unusually strong single signals to be identified.

---

### 6. Double-edged indicators

Some indicators are considered highly significant but unsuitable for automatic interpretation as strengths.

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
- Hesitant
- Detached

These indicators are stored in a controlled list:

```python
DOUBLE_EDGED_INDICATORS = {
    "stubborn",
    "rigid",
    "casual",
    "dramatic",
    "unpredictable",
    "dependent",
    "dependence",
    "vulnerability",
    "volatility",
    "impulsiveness",
    "hesitant",
    "detached",
}
```

A high value on one of these indicators should not be interpreted alone.

For example:

```text
Stubborn: STEN 10
```

may reflect:

- persistence
- conviction
- resilience in the face of opposition
- resistance to influence
- difficulty reconsidering a position
- difficulty adapting

The wider profile determines which interpretation is most plausible and what should be explored.

---

### 7. Priority level

Each Area to Explore receives a visual priority level.

For combination rules, the level is based on:

- the strongest elevated double-edged indicator
- the strongest related low-score signal

For low-score themes, the level is based on the inverse of the average score.

Example:

```text
Adapting to Change: 1
Openness to Change: 1
Adaptability: 2
```

Average:

```text
1.3
```

Visual exploration priority:

```text
approximately 10/10
```

This priority level is a UI summary.

It is not:

- a validated psychometric score
- a probability
- a diagnosis
- a prediction of performance
- an official assessment scale

It should be described as an exploration priority only.

---

### 8. Supporting indicators

Each displayed area includes the assessment indicators that triggered it.

Example:

```text
Flexibility when challenged

Supporting indicators:
- Stubborn: STEN 10
- Adapting to Change: STEN 1
- Openness to Change: STEN 1
- Flexibility: STEN 2
```

This helps users understand:

- why the area was generated
- which indicators contributed
- whether the pattern includes high, low or mixed evidence
- which original scores and scales were used

The system should avoid unexplained conclusions.

---

### 9. Interview guidance

Each Area to Explore includes:

- a description
- an “Explore through” question
- a “What to listen for” prompt
- supporting assessment indicators
- a tooltip explaining the selection logic

Example:

```text
Explore through:
Ask about a situation where the candidate needed to abandon an original plan,
accept another person’s approach or adjust quickly to unexpected change.

What to listen for:
Listen for self-awareness, openness to new information and practical strategies
for adapting without losing determination.
```

The goal is to turn assessment results into structured follow-up, rather than static labels.

---

### 10. Maximum number of areas

The system currently displays a maximum of four Areas to Explore.

Areas are sorted by:

1. exploration priority
2. number of supporting indicators

This keeps the report focused on the strongest and most relevant patterns.

---

### 11. Overlap between areas

Some indicators may support more than one Area to Explore.

Example:

```text
Adapting to Change: STEN 1
Openness to Change: STEN 1
Adaptability: STEN 2
```

may contribute to both:

- Flexibility when challenged
- Adaptability under pressure

This can be conceptually valid, but excessive overlap may make the report repetitive.

A future implementation should consider:

- prioritising combination rules over generic low-score themes
- preventing the same indicator from appearing in several similar areas
- merging closely related areas
- calculating overlap between themes
- limiting repeated evidence

---

### 12. Duplicate indicators

Assessment data may contain repeated indicator names.

The current normalisation logic removes exact duplicate names and keeps the first occurrence.

This avoids accidentally counting the same name twice, but it may also hide meaningful differences if repeated names represent:

- different competency frameworks
- different report sections
- different source constructs
- different score interpretations

A future version should use stable indicator IDs instead of relying only on text labels.

---

### 13. Interpretation principles

The Areas to Explore section follows these principles:

1. Low scores are not automatically weaknesses.
2. High scores are not automatically strengths.
3. Double-edged traits require contextual interpretation.
4. Patterns are more useful than isolated results.
5. Results should be verified through behavioural examples.
6. Supporting indicators should remain visible.
7. Original scales should be retained.
8. Priority levels are descriptive UI summaries only.
9. Wording should remain probabilistic and cautious.
10. Human professional judgement remains essential.

---

### 14. Current limitations

The current implementation is an early rule-based version.

Known limitations include:

- Combination rules have not yet been formally validated.
- Theme mappings have not yet been psychometrically reviewed.
- Thresholds are configurable but not empirically calibrated.
- Some indicators may belong to several themes.
- Similar areas may reuse the same supporting evidence.
- Duplicate names are handled simplistically.
- Some constructs may be bipolar or context-dependent.
- The system does not yet account for norm groups.
- Cultural and language differences are not yet included.
- Role context does not yet fully affect prioritisation.
- Motivation and cognitive results are not yet deeply integrated.
- Priority scores are not validated composite measures.

---

### 15. Areas for psychometric review

Behavioural scientists and psychometric specialists are invited to review:

#### Combination validity

- Are the high-low combinations conceptually defensible?
- Are any rules too broad?
- Are any rules too deterministic?
- Should more than one high or low indicator be required?

#### Thresholds

- Is STEN 8 appropriate for elevated double-edged indicators?
- Is STEN 4 appropriate for low supporting evidence?
- Should STEN 1–2 be treated differently?
- Should thresholds vary by construct?

#### Direction of interpretation

- Which indicators are problematic when high?
- Which indicators are problematic when low?
- Which are genuinely double-edged?
- Which should only be interpreted together with related constructs?

#### Overlap

- Should the same indicator support several areas?
- Should combination rules override generic theme rules?
- Should similar areas be merged automatically?

#### Language

- Are descriptions appropriately cautious?
- Do the texts distinguish preference, behaviour and capability?
- Could any wording be interpreted as diagnostic or deterministic?

#### Interview use

- Are the follow-up questions valid and useful?
- Do “What to listen for” prompts risk confirmation bias?
- Should prompts also include alternative explanations?

---

### 16. Future development

Planned improvements may include:

- psychometrically reviewed combination rules
- stable indicator IDs
- construct-specific thresholds
- better handling of bipolar traits
- contradiction detection
- overlap reduction
- alternative explanations
- confidence ratings
- role-context prioritisation
- motivation and ability integration
- automated tests using known assessment profiles
- rule versioning
- psychometric review status per theme
- audit logging of why an area was generated

---

### 17. Important disclaimer

The Areas to Explore section is intended as structured decision support.

It should not be used as:

- a standalone selection decision
- a diagnosis
- proof of a weakness
- a definitive statement about behaviour
- a replacement for trained interpretation
- a substitute for interviews, references or other evidence

Assessment results should always be interpreted in context and together with other relevant information.


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

