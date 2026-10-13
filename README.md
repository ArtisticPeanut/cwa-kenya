# Kenyan Community-Driven Cybersecurity Translation & Awareness Platform

A community-driven platform for developing, verifying and publishing cybersecurity
terminology and awareness messages in Kenyan languages and dialects — so that a
warning about a scam is **understood**, not just translated.

Built with **Python, Flask and SQLite** (migratable to PostgreSQL), with an
admin review workflow, contributor recognition, imports/exports and a read-only API.

---

## Quick start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create tables, seed reference data, import the responses CSV
python scripts\bootstrap.py

# 3. Create your first administrator (interactive)
$env:FLASK_APP = "run.py"
flask create-user      # role defaults to "admin"; derive a username automatically
flask create-user --username billy --role admin

# 4. Run the app
python run.py          # http://127.0.0.1:5000
```

> Upgrading an existing database? Add the `username` column and backfill it from
> each account's email:
>
> ```powershell
> flask migrate-usernames
> ```

To import a different responses file:

```powershell
python scripts\bootstrap.py --csv "path\to\responses.csv"
# or
flask import-csv "path\to\responses.csv"
```

The import is idempotent — re-running skips submissions that already exist.

If a respondent picked a language but listed a dialect that belongs to a
different language (e.g. "Swahili" + dialect "Kikuyu"/"Kamba"/"Kisii"), the
importer now trusts the dialect and files the row under the correct language.
To repair rows imported before this fix, run:

```powershell
flask repair-classification
```

---

## How the platform works

1. **Language & dialect selection.** Users pick the language (and optionally a
   dialect/community) they understand best. County only *suggests* languages; it
   never determines the choice. Users may keep the broader language name.
2. **Community translation tasks.** Each cybersecurity term shows a plain-English
   and Kiswahili explanation. Contributors can support an existing candidate,
   submit their own translation, explain local usage and give example warnings.
3. **Community verification.** Every submission collects assessments. The platform
   tracks support, agreement ratio, community differences and corrections.
   Popular translations become *candidates for review* — never automatic facts.
4. **Review & canonical approval.** Authorised reviewers compare candidates, approve
   a recommended/canonical version, request revisions, flag misleading entries or
   replace a previous approval. Every decision is written to an audit trail with a
   full revision history. Competing interpretations are preserved when evidence is
   insufficient.
5. **Extended explanations.** Definitions and context accompany a translation so the
   cybersecurity meaning is preserved and made culturally relevant.
6. **Contributor recognition.** Points reward demonstrated quality (approved
   translations, useful context, constructive reviews) rather than volume or
   popularity. Milestones track progress toward paid translation assignments.

---

## Project structure

```
cwa_project/
├── run.py                     # entry point
├── requirements.txt
├── pytest.ini
├── scripts/
│   └── bootstrap.py           # create tables + seed + import (one command)
├── app/
│   ├── __init__.py            # app factory, blueprints, error handlers, filters
│   ├── config.py              # dev / testing / production config
│   ├── extensions.py          # db, login manager, CSRF
│   ├── models.py              # full schema
│   ├── forms.py               # WTForms
│   ├── auth.py                # register / login / profile
│   ├── main.py                # public UI
│   ├── admin.py               # reviewer + admin dashboard
│   ├── api.py                 # read-only JSON API v1
│   ├── cli.py                 # flask commands
│   ├── services/
│   │   ├── seed_data.py       # counties, languages, terms, milestones
│   │   ├── seeding.py         # idempotent seeding
│   │   ├── importer.py        # Google Forms CSV import
│   │   ├── consensus.py       # voting, consensus, canonical approval
│   │   ├── recognition.py     # points, milestones, leaderboard
│   │   └── exporter.py        # JSON / CSV export
│   ├── templates/             # Jinja2 templates
│   └── static/                # CSS + JS
└── tests/                     # pytest suite
```

---

## Public pages

| Path | Purpose |
|---|---|
| `/` | Home & project overview |
| `/learn` | Mimo — the friendly chatbot learning experience |
| `/languages` | Language / dialect / county selection |
| `/tasks` | Translation tasks for the selected language |
| `/tasks/<term>` | Translate, explain and assess candidates |
| `/browse` | Verified glossary with filters |
| `/terms/<slug>` | A term with all verified translations |
| `/leaderboard` | Contributor recognition |
| `/me` | Your submissions, milestones and reputation |
| `/downloads` | Open data (JSON / CSV) |
| `/about` | Project vision and principles |
| `/auth/login` | Sign in with a username **or** email |
| `/auth/register` | Create a contributor account |
| `/auth/forgot` | Request a one-time reset code by email |
| `/auth/reset` | Enter the code and choose a new password |

## Accounts & password reset

- Every account has a unique **username** (3–30 letters, numbers or underscores).
  Sign in with either the username or the email address.
- **Forgot password** emails a 6-digit one-time code (`OTP_TTL_MINUTES`, default 10
  minutes, `OTP_MAX_ATTEMPTS` tries). Only a hash of the code is stored; codes are
  single-use and a fresh request invalidates earlier ones.
- With **no SMTP configured** the code is written to the console and the app log,
  so the flow works in development and demos. Set the `SMTP_*` variables below to
  send real email.

## Admin (reviewers / administrators)

| Path | Purpose |
|---|---|
| `/admin/` | Dashboard |
| `/admin/review` | Review queue (filter by language / consensus) |
| `/admin/review/<term>/<lang>` | Compare candidates & approve canonical |
| `/admin/canonical` | Canonical translations & revision history |
| `/admin/terms` | Manage glossary terms |
| `/admin/users` | Roles and status (admin only) |
| `/admin/data` | Import / export (admin only) |

## API v1

Read-only, no authentication required for approved data:

```
GET /api/v1/health
GET /api/v1/languages
GET /api/v1/counties
GET /api/v1/terms
GET /api/v1/translations                     # all verified
GET /api/v1/translations?language=Kikuyu
GET /api/v1/translations/phishing            # per term, all languages
GET /api/v1/leaderboard
POST /api/v1/token                           # JWT for future write access
```

---

## Configuration

Copy `.env.example` to `.env` and adjust. Key options:

| Variable | Meaning |
|---|---|
| `SECRET_KEY` | Flask session / CSRF secret (set a strong value in production) |
| `DATABASE_URL` | Override SQLite, e.g. `postgresql+psycopg://user:pass@host/db` |
| `MIN_VOTES_FOR_CONSENSUS` | Assessments required before review (default 3) |
| `CONSENSUS_RATIO` | Agreement needed to treat a candidate as consensus (default 0.66) |
| `AMBIGUITY_MARGIN` | Gap below which competitors are treated as ambiguous (default 0.15) |
| `WTF_CSRF_ENABLED` | Disable CSRF (tests only) |
| `SMTP_HOST` / `SMTP_PORT` | Mail server (leave blank to log codes to the console) |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP credentials |
| `SMTP_USE_TLS` | STARTTLS on port 587 (default 1); set 0 for SSL on 465 |
| `MAIL_FROM` / `MAIL_FROM_NAME` | Sender address and display name |
| `OTP_TTL_MINUTES` | Password-reset code lifetime (default 10) |
| `OTP_MAX_ATTEMPTS` | Wrong-code attempts allowed per code (default 5) |

---

## Data model (highlights)

- **Reference:** `counties`, `languages`, `dialects`, `language_counties`, `terms`
- **Contributors:** `users`, `submissions`, `votes`, `reviews`
- **Output:** `canonical_translations`, `canonical_revisions` (full audit history)
- **Recognition:** `milestones`, `user_milestones`, `contributions` (append-only ledger)

Imported Google Forms responses create *seed contributors* (no password, cannot
sign in) so real samples participate in community verification without exposing
anyone's login.

---

## Tests

```powershell
python -m pytest
```

Covers reference data, the public routes, registration, submission, self-vote
protection, consensus (reached and ambiguous), canonical approval + revision
history, milestones, exports and the API.

---

## Migrating to PostgreSQL

Set `DATABASE_URL` to a PostgreSQL DSN and run `flask init-db` / `flask seed`.
No code changes are required — the models are database-agnostic.
