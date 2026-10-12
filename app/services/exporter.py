"""Export approved translations in machine-readable formats (JSON / CSV)."""

import csv
import io
import json

from app.models import CANON_APPROVED, CanonicalTranslation, Submission


def approved_records(include_unapproved=False):
    query = CanonicalTranslation.query
    if not include_unapproved:
        query = query.filter(CanonicalTranslation.status == CANON_APPROVED)
    records = []
    for canon in query.order_by(
        CanonicalTranslation.term_id, CanonicalTranslation.language_id
    ).all():
        records.append(
            {
                "term": canon.term.english_name,
                "term_slug": canon.term.slug,
                "category": canon.term.category,
                "english_definition": canon.term.english_definition,
                "swahili_name": canon.term.swahili_name,
                "swahili_definition": canon.term.swahili_definition,
                "language": canon.language.name,
                "dialect": canon.dialect.name if canon.dialect else None,
                "translation": canon.text,
                "definition": canon.definition,
                "context": canon.context,
                "status": canon.status,
                "revision": canon.revision_no,
                "approved_at": canon.approved_at.isoformat()
                if canon.approved_at else None,
            }
        )
    return records


def to_json(include_unapproved=False, indent=2):
    payload = {
        "generated_by": "CWA Kenya translation platform",
        "count": None,
        "translations": approved_records(include_unapproved=include_unapproved),
    }
    payload["count"] = len(payload["translations"])
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def to_csv(include_unapproved=False):
    records = approved_records(include_unapproved=include_unapproved)
    buffer = io.StringIO()
    fieldnames = [
        "term", "term_slug", "category", "language", "dialect", "translation",
        "definition", "context", "status", "revision", "approved_at",
        "english_definition", "swahili_name", "swahili_definition",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(record)
    return buffer.getvalue()


def to_submissions_csv():
    buffer = io.StringIO()
    fieldnames = [
        "submission_id", "term", "language", "dialect", "text", "usage_note",
        "example", "status", "support", "oppose", "contributor", "consent_public",
        "created_at",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for sub in Submission.query.order_by(Submission.id).all():
        writer.writerow(
            {
                "submission_id": sub.id,
                "term": sub.term.english_name,
                "language": sub.language.name,
                "dialect": sub.dialect.name if sub.dialect else "",
                "text": sub.text,
                "usage_note": sub.usage_note or "",
                "example": sub.example or "",
                "status": sub.status,
                "support": sub.support_count,
                "oppose": sub.oppose_count,
                "contributor": sub.user.display_name if sub.user else "",
                "consent_public": sub.consent_public,
                "created_at": sub.created_at.isoformat() if sub.created_at else "",
            }
        )
    return buffer.getvalue()
