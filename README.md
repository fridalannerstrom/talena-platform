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



---


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

