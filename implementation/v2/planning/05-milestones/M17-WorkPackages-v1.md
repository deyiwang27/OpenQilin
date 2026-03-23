# M17 Work Packages — Open-Source and Sponsorship Readiness

Milestone: `M17`
Status: `planned`
Entry gate: M16 complete (full runtime polished and stable)
Supporting docs: `03-community/OpenSourceCommunityStrategy-v1.md`, `03-community/FundingAndSponsorshipStrategy-v1.md`

---

## Milestone Goal

Prepare OpenQilin for public introduction, early contributors, and realistic sponsorship and startup-credit outreach. The runtime is complete; this milestone makes it presentable, discoverable, and inviting. Every deliverable here should be usable for real outreach before or immediately after public launch.

---

## WP M17-01 — Public README and Repository Clarity

**Goal:** Make the repository understandable to a first-time visitor in under 10 minutes. Replace any internal-only framing with a clear public product story.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.2`

### Tasks

- [x] Write root `README.md` with sections:
  - **What is OpenQilin?** — 2-sentence product thesis: governed AI operating system for the solopreneur
  - **Why?** — pain it solves: coordination noise, cost opacity, role sprawl
  - **How it works** — 3-5 bullet overview: Discord surface + constitutional governance + project-space routing + Grafana visibility
  - **Status** — MVP-v2 complete; Secretary/CSO/DL/PM/CEO/CWO/Auditor/Administrator/Specialist activation
  - **Quick start** — prerequisites, `docker compose up`, first interaction
  - **Architecture** — link to `spec/architecture/ArchitectureBaseline-v1.md`
  - **Roadmap** — link to roadmap doc (WP M17-02)
  - **Contributing** — link to `CONTRIBUTING.md` (WP M17-04)
  - **License** — confirm license file present (`LICENSE`)
- [x] Ensure `LICENSE` file exists (MIT or Apache 2.0; confirm with project owner) — Apache 2.0 confirmed present
- [x] Review and update `compose.yml` and environment variable docs to reflect the real MVP-v2 topology (not v1 placeholder comments)
- [x] Review `spec/` directory: confirm no internal-only or placeholder docs are exposed without clear status labels — grep returned no matches

### Outputs

- Clear, public-facing `README.md`
- `LICENSE` file present
- Compose and env docs accurate for the real MVP-v2 stack

### Done criteria

- [x] A new visitor can understand what OpenQilin is, why it exists, and how to try it in under 10 minutes of repo exploration
- [x] Quick start actually works end-to-end on a clean machine
- [x] No stale internal-only framing in root-visible files — WP-reference comments removed from compose.yml and .env.example

---

## WP M17-02 — Roadmap

**Goal:** Publish a public roadmap that makes OpenQilin's direction legible and investable for contributors and potential sponsors.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.3`

### Tasks

- [x] Create `ROADMAP.md` at repo root with:
  - **Completed (MVP-v1)** — what v1 proved: institutional role presence, project governance, governed tool flows
  - **Completed (MVP-v2)** — what v2 delivers: real OPA enforcement, PostgreSQL persistence, LangGraph orchestration, Grafana dashboard, free-text UX, Secretary/CSO/DL activation
  - **Next (post-MVP-v2)** — high-level directions: full sandbox isolation, broader chat adapter support, OpenQilin console, sponsor/community growth
  - **Non-goals** — what OpenQilin is deliberately not: general AI framework, multi-user SaaS, code generation tool
- [x] Keep roadmap items as themes/goals, not deadlines

### Outputs

- `ROADMAP.md` at repo root
- Linked from `README.md`

### Done criteria

- [x] Roadmap is legible to an external reader with no prior context
- [x] MVP-v2 items are marked complete
- [x] Post-MVP directions are framed as themes, not timelines

---

## WP M17-03 — Demo Assets

**Goal:** Create a reusable, convincing end-to-end demo that showcases the solopreneur use case. Demo should work for outreach, README, and presentations.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.2`

### Tasks

- [ ] Write demo script: one concrete solopreneur workflow end-to-end:
  1. Owner creates a project via Discord (`/oq create project "Website Redesign"`)
  2. PM responds in project space; DL escalation visible when needed
  3. Budget allocation visible in Grafana Budget panel
  4. CSO governance gate visible on a policy-sensitive action
  5. Owner views blocked task and approves in Discord
  6. Audit trail visible in Grafana Audit panel
- [ ] Record demo as screen recording (or animated GIF for README) — narrated or captioned
- [ ] Write companion `docs/demo/` folder with step-by-step text walkthrough usable in README and outreach
- [ ] Confirm demo runs on a clean `docker compose up` without manual setup beyond `.env` config

### Outputs

- Demo script and screen recording / GIF
- `docs/demo/` walkthrough text
- Demo runnable from clean checkout

### Done criteria

- [ ] Demo showcases governance, project execution, budget visibility, and audit trail
- [ ] Demo runs on clean checkout without prior context
- [ ] Demo asset usable in GitHub README, social media post, and sponsorship deck

---

## WP M17-04 — Contributor Entry Path

**Goal:** Make it possible for an external contributor to find, understand, and begin contributing to OpenQilin without needing private context.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.4`

### Tasks

- [x] Write `CONTRIBUTING.md`:
  - **How to set up** — prerequisites, clone, `docker compose up`, run tests
  - **How the codebase is organized** — link to `spec/architecture/ArchitectureBaseline-v1.md` and `design/v2/README.md`
  - **Where to start** — point to `good first issue` label; suggest reading path
  - **How to submit a PR** — branch naming, PR format, review expectations
  - **Code of conduct** — short, standard CoC or link to `CODE_OF_CONDUCT.md`
- [x] Write `CODE_OF_CONDUCT.md` (Contributor Covenant or equivalent)
- [x] Label 3–5 existing issues as `good first issue` in GitHub with clear descriptions
- [x] Confirm test suite runs cleanly from a clean clone: `pytest` passes without manual data seeding

### Outputs

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- 3–5 labeled `good first issue` GitHub issues

### Done criteria

- [x] External contributor can set up and run tests in under 30 minutes using `CONTRIBUTING.md` alone
- [x] At least 3 `good first issue` issues exist with scope, context, and expected outcome described
- [x] `CONTRIBUTING.md` linked from `README.md`

---

## WP M17-05 — Website and Public Presence

**Goal:** Establish a minimal public web presence with a domain, landing page, and contact email. Required for sponsorship applications and contributor discovery.

**Design ref:** `03-community/FundingAndSponsorshipStrategy-v1.md §4.2`

### Tasks

- [ ] Acquire or confirm domain (e.g. `openqilin.dev` or equivalent)
- [ ] Build minimal landing page (single-page; no CMS required):
  - Product one-liner and thesis
  - Link to GitHub repo
  - Link to demo / quick start
  - Contact email (`hello@<domain>` or equivalent)
  - "Star on GitHub" CTA
- [ ] Set up `hello@<domain>` or equivalent contact email
- [ ] Add website link to GitHub repo description and `README.md`

### Outputs

- Public domain with live landing page
- Public contact email operational

### Done criteria

- [ ] Landing page live at public domain
- [ ] Contact email receives test message
- [ ] Website URL in GitHub repo description and `README.md`

---

## WP M17-06 — Sponsorship and Startup-Credit Readiness

**Goal:** Prepare the minimum assets needed to apply to startup and sponsorship programs credibly.

**Design ref:** `03-community/FundingAndSponsorshipStrategy-v1.md §4`

### Tasks

- [ ] Write one-page project summary (PDF or Markdown → PDF):
  - What OpenQilin is and who it is for
  - What MVP-v2 delivers
  - Current traction (GitHub stars, contributors if any, demo link)
  - What resources would unlock (compute, LLM API credits, infra)
  - Contact info
- [ ] Identify and shortlist target programs to apply to:
  - AWS Activate / Google for Startups (cloud compute credits)
  - GitHub Sponsors (community funding)
  - Anthropic / Google / relevant LLM provider developer programs
  - Open-source foundation grants if eligible
- [ ] Set up GitHub Sponsors profile (even if starting at $0)
- [ ] Add FUNDING.yml to repo root pointing to GitHub Sponsors

### Outputs

- One-page project summary asset
- Target program shortlist
- GitHub Sponsors profile active
- `FUNDING.yml` in repo root

### Done criteria

- [ ] One-page summary ready to attach to any program application
- [ ] GitHub Sponsors profile live (even at zero sponsors)
- [ ] `FUNDING.yml` in repo root
- [ ] At least one sponsorship/credit program application submitted or scheduled

---

## M17 Exit Criteria

- [ ] All six WPs above are marked done
- [ ] README, CONTRIBUTING.md, CODE_OF_CONDUCT.md, ROADMAP.md all live in repo root
- [ ] Demo runs end-to-end on clean checkout
- [ ] Public domain and contact email live
- [ ] GitHub Sponsors profile active
- [ ] At least one sponsorship/credit program application submitted
- [ ] A new visitor can understand, try, and begin contributing to OpenQilin without prior context

## References

- `03-community/OpenSourceCommunityStrategy-v1.md`
- `03-community/FundingAndSponsorshipStrategy-v1.md`
- `00-direction/MvpV2SuccessCriteria-v1.md §4.8`
