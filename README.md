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
> each account's email, then add the email-verification columns (existing
> accounts are treated as already verified so nobody is locked out):
>
> ```powershell
> flask migrate-usernames
> flask migrate-email-verification
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
├── data/
│   └── seed/
│       └── submissions.csv    # anonymized responses (emails -> @import.local)
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
| `/auth/verify` | Confirm your email with the 6-digit code |
| `/auth/forgot` | Request a one-time reset code by email |
| `/auth/reset` | Enter the code and choose a new password |

## Learning with Mimo

- `/learn` is Mimo's chat playground: pick a language, then ask for a 🛡️ safety
  tip, 📖 a word, or a 🎯 quiz.
- Once a language is chosen, Mimo can also **speak a specific dialect** (pills
  under the language row, with the current pick shown as a chip in the chat
  header). Words, quizzes and tips then prefer content tagged with that dialect,
  falling back to the whole language when the community has none. Your choice is
  remembered per language in the browser.
- The dialect switcher only appears for languages that actually have
  dialect-tagged content, and it never changes the site-wide selected language.

## Accounts, verification & password reset

- Every account has a unique **username** (3–30 letters, numbers or underscores).
  Sign in with either the username or the email address.
- **Email verification at sign-up.** Registering sends a 6-digit code; the account
  stays inactive and **cannot sign in until the code is confirmed** at `/auth/verify`.
  A "Resend code" button issues a fresh code (60-second cooldown) and invalidates
  the previous one. Verification is **self-contained**: the page accepts the email
  plus the code, so a user who lost their session, closed the tab or switched
  device can still confirm (reachable from a "Verify your email" link on the sign-in
  and registration pages).
- Accounts that already existed before verification was introduced are marked
  verified by `flask migrate-email-verification`, so nobody is locked out.
- **Forgot password** emails a 6-digit one-time code (`OTP_TTL_MINUTES`, default 10
  minutes, `OTP_MAX_ATTEMPTS` tries). Only a hash of the code is stored; codes are
  single-use and a fresh request invalidates earlier ones.
- With **no email provider configured** the code is written to the console and the
  app log, so the flow works in development and demos. Configure either the
  `SMTP_*` variables or an HTTPS email API key (`BREVO_API_KEY` / `RESEND_API_KEY`)
  to send real email — see the table below.
- **Google Sign-In (optional).** Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
  and a "Continue with Google" button appears on the sign-in and registration
  pages. Google accounts are trusted as verified (no OTP needed); a first-time
  Google sign-in creates the account with an auto-generated username (editable in
  the profile), and an existing account with the same email is linked. Setup:
  1. In the [Google Cloud Console](https://console.cloud.google.com/) create an
     **OAuth client ID** of type *Web application*.
  2. Add an authorised redirect URI: `<APP_URL>/auth/google/callback`
     (e.g. `https://cwa-kenya.onrender.com/auth/google/callback`, and
     `http://127.0.0.1:5000/auth/google/callback` for local testing).
  3. Copy the client ID/secret into the env vars above. Locally, also set
     `OAUTHLIB_INSECURE_TRANSPORT=1` so the HTTP callback is accepted.
  Leave both blank to keep the button hidden.

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
| `SECRET_KEY` | Flask session / CSRF secret. **Required in production** (≥32 chars, not a placeholder) — the app refuses to boot otherwise. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `FLASK_ENV` | `development` (default), `testing`, or `production` |
| `DATABASE_URL` | Override SQLite, e.g. `postgresql+psycopg://user:pass@host/db` |
| `MIN_VOTES_FOR_CONSENSUS` | Assessments required before review (default 3) |
| `CONSENSUS_RATIO` | Agreement needed to treat a candidate as consensus (default 0.66) |
| `AMBIGUITY_MARGIN` | Gap below which competitors are treated as ambiguous (default 0.15) |
| `WTF_CSRF_ENABLED` | Disable CSRF (tests only) |
| `RATELIMIT_STORAGE_URI` | Rate-limit store; default `memory://`, use `redis://…` with multiple workers |
| `TRUST_PROXY` | Set `1` behind a reverse proxy so the real client IP / HTTPS is detected |
| `SMTP_HOST` / `SMTP_PORT` | Mail server (leave blank to log codes to the console) |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP credentials |
| `SMTP_USE_TLS` | STARTTLS on port 587 (default 1); set 0 for SSL on 465 |
| `MAIL_FROM` / `MAIL_FROM_NAME` | Sender address and display name |
| `BREVO_API_KEY` | Optional HTTPS email API (port 443). Use where outbound SMTP is blocked (e.g. Render free plan) |
| `RESEND_API_KEY` | Optional HTTPS email API alternative; requires a verified sending domain |
| `OTP_TTL_MINUTES` | Lifetime of sign-up verification & password-reset codes (default 10) |
| `OTP_MAX_ATTEMPTS` | Wrong-code attempts allowed per code (default 5) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional Google Sign-In credentials; leave blank to hide the button |

---

## Deploying & hosting

The dev runner (`python run.py`) is **not** for production. Use the WSGI
entrypoint `wsgi.py` (it defaults to the production config):

```powershell
# Linux / macOS
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app

# Windows
waitress-serve --listen=0.0.0.0:8000 wsgi:app
```

Before you invite users, make sure you have:

1. **A strong `SECRET_KEY`** — the app refuses to start in production without one.
2. **Debug off** — `wsgi.py` uses `ProductionConfig` (`DEBUG=False`), so the
   Werkzeug debugger is never exposed. Never serve `run.py` publicly.
3. **A real database** — set `DATABASE_URL` to PostgreSQL for concurrent traffic
   (SQLite is fine for development and small demos only).
4. **HTTPS + a reverse proxy** — terminate TLS at Nginx/Heroku/Render, then set
   `TRUST_PROXY=1` so client IPs and secure-cookie detection work.
5. **Shared rate-limit storage** — with more than one worker, set
   `RATELIMIT_STORAGE_URI` to Redis so login limits are enforced across workers.

### Login & account safety

- Passwords are hashed with Werkzeug (scrypt) and reset/verification codes are
  hashed too.
- New accounts must **confirm their email** before they can sign in; verification
  codes are single-use, expire after `OTP_TTL_MINUTES`, and allow
  `OTP_MAX_ATTEMPTS` tries.
- Sign-in, registration, password reset and resend are **rate limited** (`10/min`
  login, `20/hr` register, `5/min` forgot, `10/min` reset, `5/min` resend) per
  client IP.
- The `next=` redirect after sign-in only accepts same-site paths (no open redirect).
- Reset codes are single-use, expire after `OTP_TTL_MINUTES`, and allow
  `OTP_MAX_ATTEMPTS` tries before a new code is required.
- Session and "remember me" cookies are `HttpOnly`, `SameSite=Lax`, and `Secure`
  in production. CSRF protection is enabled on every form.


---

## Data model (highlights)

- **Reference:** `counties`, `languages`, `dialects`, `language_counties`, `terms`
- **Contributors:** `users`, `submissions`, `votes`, `reviews`,
  `password_reset_otps`, `email_verification_otps`
- **Output:** `canonical_translations`, `canonical_revisions` (full audit history)
- **Recognition:** `milestones`, `user_milestones`, `contributions` (append-only ledger)

Imported Google Forms responses create *seed contributors* (no password, cannot
sign in) so real samples participate in community verification without exposing
anyone's login.

The committed `data/seed/submissions.csv` is an **anonymized** copy of the source
responses: contributor emails are replaced with `<handle>@import.local` (the
handle keeps the display name), so the sample dataset can ship in the repo and be
loaded with `flask import-csv data/seed/submissions.csv`. The original responses
CSV (with real emails) stays out of git. Deployments re-run the import on each
boot because the free-plan database is ephemeral.

---

## Tests

```powershell
python -m pytest
```

Covers reference data, the public routes, registration, submission, self-vote
protection, consensus (reached and ambiguous), canonical approval + revision
history, milestones, exports and the API. Auth tests also cover the login
redirect guard, production `SECRET_KEY` enforcement, and rate limiting.

---

## Migrating to PostgreSQL

Set `DATABASE_URL` to a PostgreSQL DSN and run `flask init-db` / `flask seed`.
No code changes are required — the models are database-agnostic.
