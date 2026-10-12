"""Import existing Google Forms responses into the platform.

The source CSV has one row per contributor and one column per term, e.g.
``Translate: Phishing``. Each non-empty cell becomes a candidate submission
attributed to a seed contributor account (no password, cannot log in).

The import is idempotent: re-running skips rows that were already imported.
"""

import os
import re

import pandas as pd

from app.extensions import db
from app.models import (
    County,
    Dialect,
    Language,
    STATUS_CANDIDATE,
    Submission,
    Term,
    User,
)
from app.services import seeding

# Map the varied spellings found in real responses onto seeded languages.
LANGUAGE_ALIASES = {
    "swahili": "Kiswahili",
    "kiswahili": "Kiswahili",
    "swa": "Kiswahili",
    "kimeru": "Kimeru",
    "meru": "Kimeru",
    "kikuyu": "Kikuyu",
    "gikuyu": "Kikuyu",
    "abagusii": "Ekegusii",
    "kisii": "Ekegusii",
    "gusii": "Ekegusii",
    "ekegusii": "Ekegusii",
    "kamba": "Kikamba",
    "kikamba": "Kikamba",
    "luo": "Dholuo",
    "dholuo": "Dholuo",
    "luhya": "Luhya",
    "kalenjin": "Kalenjin",
    "maasai": "Maasai",
    "maa": "Maasai",
    "somali": "Somali",
    "mijikenda": "Mijikenda",
    "taita": "Taita",
    "teso": "Teso",
    "kuria": "Kuria",
    "embu": "Kiembu",
    "kiembu": "Kiembu",
    "tharaka": "Kitharaka",
    "kitharaka": "Kitharaka",
    "samburu": "Samburu",
    "borana": "Borana",
    "rendille": "Rendille",
    "turkana": "Turkana",
}


def _norm(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _key(value):
    return _norm(value).casefold()


def resolve_language(raw):
    name = LANGUAGE_ALIASES.get(_key(raw))
    if name:
        return Language.query.filter_by(name=name).first()
    return Language.query.filter(db.func.lower(Language.name) == _key(raw)).first()


def resolve_county(raw):
    if not _norm(raw):
        return None
    return County.query.filter(db.func.lower(County.name) == _key(raw)).first()


def resolve_dialect(language, raw):
    """Find or create a dialect under the selected language."""
    name = _norm(raw)
    if not name:
        return None
    existing = Dialect.query.filter(
        Dialect.language_id == language.id,
        db.func.lower(Dialect.name) == _key(name),
    ).first()
    if existing:
        return existing
    # Treat a bare language name as the language's standard dialect.
    if _key(name) == _key(language.name):
        name = f"Standard {language.name}"
        existing = Dialect.query.filter(
            Dialect.language_id == language.id,
            db.func.lower(Dialect.name) == _key(name),
        ).first()
        if existing:
            return existing
    dialect = Dialect(language_id=language.id, name=name.title())
    db.session.add(dialect)
    db.session.flush()
    return dialect


def get_or_create_seed_user(email, county=None):
    email = _norm(email).lower()
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    local = email.split("@")[0] if email else "contributor"
    display = local.replace(".", " ").replace("_", " ").strip().title() or "Contributor"
    user = User(
        email=email or f"seed-{db.session.query(User).count() + 1}@import.local",
        display_name=display,
        role="contributor",
        is_seed=True,
        is_active=True,
        county_id=county.id if county else None,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _is_yes(value):
    return _key(value) in {"yes", "y", "true", "ndiyo", "sawa"}


def import_csv(path, verbose=True):
    seeding.seed_all(verbose=False)

    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.columns = [_norm(c).lstrip("\ufeff") for c in df.columns]

    # Map the "Translate: X" source columns to terms.
    terms = {t.source_column: t for t in Term.query.all() if t.source_column}

    stats = {
        "rows": 0,
        "submissions": 0,
        "skipped": 0,
        "users": 0,
        "unresolved_language": 0,
    }

    for _, row in df.iterrows():
        stats["rows"] += 1
        language = resolve_language(row.get("Language"))
        # The Dialect column is often the more reliable signal: some
        # respondents picked "Swahili" but listed (and wrote in) Kikuyu,
        # Kamba, Kisii, etc. Trust the dialect when it names another language.
        implied = resolve_language(row.get("Dialect"))
        if implied and (language is None or implied.id != language.id):
            if language is not None and verbose:
                print(
                    f"  ~ reclassifying {row.get('Language')!r} -> "
                    f"{implied.name!r} (dialect {row.get('Dialect')!r})"
                )
            language = implied
        if not language:
            stats["unresolved_language"] += 1
            if verbose:
                print(f"  ! could not resolve language: {row.get('Language')!r}")
            continue

        county = resolve_county(row.get("County"))
        dialect = resolve_dialect(language, row.get("Dialect"))
        consent = _is_yes(row.get(
            "Do you allow your translations to be used in a public "
            "cybersecurity awareness project?"
        ))

        before = User.query.count()
        user = get_or_create_seed_user(row.get("Email address"), county)
        if User.query.count() > before:
            stats["users"] += 1

        if user.county_id is None and county:
            user.county_id = county.id

        for column, term in terms.items():
            text = _norm(row.get(column))
            if not text:
                continue
            exists = Submission.query.filter_by(
                term_id=term.id,
                language_id=language.id,
                dialect_id=dialect.id if dialect else None,
                user_id=user.id,
            ).first()
            if exists:
                stats["skipped"] += 1
                continue
            db.session.add(
                Submission(
                    term_id=term.id,
                    language_id=language.id,
                    dialect_id=dialect.id if dialect else None,
                    user_id=user.id,
                    text=text,
                    status=STATUS_CANDIDATE,
                    is_seed=True,
                    consent_public=consent,
                )
            )
            stats["submissions"] += 1

    db.session.commit()
    if verbose:
        print(
            "Import complete: "
            f"{stats['submissions']} submissions, "
            f"{stats['users']} contributors, "
            f"{stats['skipped']} duplicates skipped."
        )
    return stats


def repair_misclassified(verbose=True):
    """Reclassify submissions whose dialect names a different language.

    Fixes imported rows where the respondent selected one language (commonly
    "Swahili") yet listed a dialect — and wrote text — in another language,
    e.g. Kikuyu, Kamba or Kisii. The submission (and its dialect) is moved to
    the language its dialect actually belongs to.
    """
    moved = 0
    merged = 0
    touched_langs = set()

    submissions = Submission.query.filter(Submission.dialect_id.isnot(None)).all()
    for sub in submissions:
        dname = sub.dialect.name if sub.dialect else None
        target = resolve_language(dname) if dname else None
        if not target or target.id == sub.language_id:
            continue

        new_dialect = resolve_dialect(target, dname)
        duplicate = (
            Submission.query.filter_by(
                term_id=sub.term_id,
                language_id=target.id,
                dialect_id=new_dialect.id if new_dialect else None,
                user_id=sub.user_id,
            )
            .filter(Submission.id != sub.id)
            .first()
        )
        touched_langs.add((sub.language_id, target.id))
        if duplicate:
            db.session.delete(sub)
            merged += 1
            continue

        sub.language_id = target.id
        sub.dialect_id = new_dialect.id if new_dialect else None
        moved += 1

    db.session.flush()

    # Drop now-empty dialects that sit under the wrong language.
    removed_dialects = 0
    for dialect in Dialect.query.all():
        target = resolve_language(dialect.name)
        if not target or target.id == dialect.language_id:
            continue
        if dialect.name.startswith("Standard "):
            continue
        in_use = Submission.query.filter_by(dialect_id=dialect.id).count()
        if in_use == 0:
            db.session.delete(dialect)
            removed_dialects += 1

    db.session.commit()
    result = {"moved": moved, "merged": merged, "removed_dialects": removed_dialects}
    if verbose:
        print(
            f"Repair complete: moved {moved}, merged {merged} duplicates, "
            f"removed {removed_dialects} misplaced dialects."
        )
    return result
