# Business Requirements Document (BRD)
## Beko AI-Enhanced Jira Project Management System
**Version:** 1.0  
**Date:** May 2026  
**Prepared by:** Selin İnan / Zeynep Uzun  
**Supervisor:** Alper Öner  
**Stakeholder:**  (Beko, IT Project Management)

---

## 1. Project Overview

This project aims to build an AI-powered layer on top of Jira that assists Beko's project managers, developers, and warehouse staff in managing software projects more effectively. The system uses AI agents to automate sprint analysis, capacity planning, task validation, and requirement alignment — reducing manual effort and improving decision quality.

---

## 2. Stakeholders

| Role | Name / Group | Interest |
|---|---|---|
| Primary Sponsor | Beko IT Management | System adoption, ROI |
| Project Manager | PM team at Beko | Sprint planning, capacity reports, Teams summaries |
| Developer | Dev team at Beko | Task assignment, workload visibility |
| Warehouse Staff | Logistics team | Product catalog, stock management |
| System Administrator | IT Admin | User access, RBAC management |
| AI System | Automated agents | Data analysis, report generation |

---

## 3. Business Goals

### GOAL-01 — Secure Authentication
Implement secure Single Sign-On (SSO) authentication using Azure AD / OAuth 2.0 for all Beko corporate account holders. No separate password should be required; login must redirect through Microsoft's identity platform.

**Acceptance Criteria:**
- Login screen redirects to Azure AD / Microsoft login page.
- Successful authentication lands on the main dashboard.
- Failed authentication shows a clear error message.
- Sessions expire automatically after 8 hours of inactivity.

---

### GOAL-02 — Role-Based Access Control (RBAC)
Build a Role-Based Access Control system that enforces three distinct permission levels: Project Manager (PM), Developer, and Viewer. Role assignments must be manageable by a System Administrator through a dedicated UI.

**Acceptance Criteria:**
- Admin can assign or change user roles from the management screen.
- Role changes take effect immediately without requiring re-login.
- Every role modification is recorded in the audit log automatically.

---

### GOAL-03 — Audit Log System
Create a system that tracks and stores user activities for the last 30 days. Project Managers must be able to view, filter, and export activity logs. Standard users must not be able to see other users' logs.

**Acceptance Criteria:**
- PM can view a complete 30-day activity log for all users.
- Date filtering works correctly within the 30-day window.
- Logs can be exported as an Excel (.xlsx) file.
- Standard users are restricted from accessing other users' logs (403 response).

---

### GOAL-04 — Product Catalog and Inventory Module
Develop a product catalog system for warehouse staff and product managers. The system must support rapid product searches by name or barcode, with pagination and stock-level color indicators.

**Acceptance Criteria:**
- Product list displays up to 50 items per page with working pagination.
- Search by name or barcode returns results within 2 seconds.
- In-stock products display a green indicator; out-of-stock show red.

---

### GOAL-05 — Product Filtering
Enable users to filter the product catalog by category and price range simultaneously. Filters must update the list in real time without a full page reload.

**Acceptance Criteria:**
- Category dropdown and min/max price inputs work independently and together.
- Multiple filters can be applied simultaneously.
- "Clear Filters" button resets the view to the full default list.
- Empty filter results display a "No products found" message.

---

### GOAL-06 — Critical Stock Alert System
Automatically send an email notification to the responsible team when a product's stock quantity drops below 10 units following any stock update. No manual trigger should be required.

**Acceptance Criteria:**
- Email fires automatically when stock update causes quantity to drop below 10.
- Email includes product name, product ID, and updated stock quantity.
- Notification is delivered within 30 seconds of the triggering update.
- No email is sent when stock remains at 10 or above.

---

### GOAL-07 — AI Sprint Health Analysis
Build an AI agent that analyzes the active sprint's health by evaluating task statuses, risk scores, and delay signals. The agent must produce a structured report with risk levels and actionable recommendations.

**Acceptance Criteria:**
- Agent correctly identifies delayed and high-risk tasks.
- Risk score is calculated per task (1.0 = low, 3.0 = high).
- Sprint health report is generated in under 30 seconds.
- Report is accessible via the `/analyze/sprint` FastAPI endpoint.

---

### GOAL-08 — Capacity Planning Report
Generate a capacity report before each sprint starts that compares total assigned work hours against each team member's available capacity. The report must include an AI-generated English summary.

**Acceptance Criteria:**
- System compares assigned story points / hours against team capacity per person.
- Overloaded team members are flagged clearly in the report.
- Claude API generates a concise English summary of capacity status.
- Full report is generated in under 30 seconds via `/analyze/capacity` endpoint.

---

### GOAL-09 — Daily Teams Sprint Summary
Automatically deliver a sprint status summary to the Project Manager via Microsoft Teams every morning at 09:00 Istanbul time. The summary must be generated by the AI sprint analysis agent.

**Acceptance Criteria:**
- n8n workflow triggers at exactly 09:00 AM (Europe/Istanbul timezone) daily.
- Summary includes: completed tasks count, delayed tasks, high-risk items, AI English summary.
- If no active sprint exists, workflow terminates without sending a message.
- Workflow errors are logged in n8n; no silent failures.

---

### GOAL-10 — FastAPI Agent Endpoints
Expose all AI agents as HTTP endpoints via FastAPI so that n8n workflows and the dashboard UI can consume them programmatically.

**Acceptance Criteria:**
- `/analyze/sprint` returns a structured JSON sprint health report.
- `/analyze/capacity` returns a structured JSON capacity report.
- `/support/ask` accepts a question payload and returns an AI answer.
- `/health` returns `{"status": "ok"}` with HTTP 200.
- Swagger UI (`/docs`) is available and documents all endpoints.

---

### GOAL-11 — n8n Jira Webhook Listener
Configure n8n to listen for `issue_created` Jira webhook events and automatically trigger the appropriate AI agent. The AI analysis result must be posted back as a Jira issue comment.

**Acceptance Criteria:**
- Jira `issue_created` webhook is configured and sends payload to n8n within 5 seconds.
- n8n triggers the FastAPI AI endpoint upon receiving the webhook.
- AI response is posted back to the triggering Jira issue as a comment.
- API errors are caught and logged; no silent failures or crashes.

---

### GOAL-12 — BRD Alignment Scoring
When a new Jira task is created, automatically calculate a 1-10 alignment score measuring how much the task contributes to this BRD. Low-alignment tasks (score < 5) must be flagged with a comment and a "Low Alignment" label.

**Acceptance Criteria:**
- Task creation triggers the Requirement/BRD Alignment Agent automatically.
- Agent posts a 1-10 BRD Alignment Score in the Jira issue comments.
- If score < 5, a "Low Alignment" label is added and an English justification is provided.
- Score is calculated using this BRD document as the reference.

---

### GOAL-13 — Secure Environment Configuration
Ensure all credentials, API keys, and tokens are stored in environment variables and never committed to source code. The developer environment must be reproducible from a `.env.example` template.

**Acceptance Criteria:**
- `.env.example` is committed to the repository with placeholder values only.
- `.gitignore` explicitly excludes the real `.env` file.
- `config.py` reads all values using `python-dotenv` at startup.
- Application raises a clear error on startup if any required variable is missing.

---

## 4. Out of Scope

- Mobile application development.
- Integration with ERP systems (SAP, Oracle) beyond what Jira provides.
- Custom Jira plugin development (Jira Forge / Connect).
- Machine learning model training (pre-trained Claude/GPT APIs are used).
- Multi-language UI (English-only interface is acceptable for this phase).

---

## 5. Constraints

- The system must use the Anthropic Claude API or OpenAI API for AI summarization.
- Jira Cloud is the only supported Jira deployment type.
- n8n must be used as the automation/orchestration layer.
- All secrets must be stored in `.env` files, never hardcoded.
- The MCP (Model Context Protocol) architecture must be used for context delivery to AI agents.

---

## 6. Success Metrics

| Metric | Target |
|---|---|
| BRD goal coverage in Jira | ≥ 90% of goals have at least one linked Story |
| Sprint report generation time | < 30 seconds |
| Capacity report generation time | < 30 seconds |
| Daily Teams notification uptime | ≥ 95% delivery rate |
| Task BRD alignment score (avg) | ≥ 7.0 / 10 |
| Low-alignment tasks auto-flagged | 100% of tasks scoring < 5 |
