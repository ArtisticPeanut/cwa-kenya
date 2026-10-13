"""Read-only JSON API (v1) for supplying verified translations to other tools."""

from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import (
    CANON_APPROVED,
    CanonicalTranslation,
    County,
    Dialect,
    Language,
    Submission,
    Term,
    User,
    Vote,
)
from app.services import recognition

api_bp = Blueprint("api", __name__)


def _term_json(term):
    return {
        "slug": term.slug,
        "name": term.english_name,
        "category": term.category,
        "definition": term.english_definition,
        "swahili_name": term.swahili_name,
        "swahili_definition": term.swahili_definition,
    }


def _translation_json(canon):
    return {
        "term": canon.term.slug,
        "term_name": canon.term.english_name,
        "category": canon.term.category,
        "language": canon.language.name,
        "dialect": canon.dialect.name if canon.dialect else None,
        "translation": canon.text,
        "definition": canon.definition,
        "context": canon.context,
        "status": canon.status,
        "revision": canon.revision_no,
        "approved_at": canon.approved_at.isoformat() if canon.approved_at else None,
    }


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "cwa-kenya-api", "version": "v1"})


@api_bp.route("/stats")
def stats():
    """Engagement snapshot used by the learners interface."""
    sub_by_lang = dict(
        db.session.query(Submission.language_id, func.count(Submission.id))
        .group_by(Submission.language_id)
        .all()
    )
    approved_by_lang = dict(
        db.session.query(
            CanonicalTranslation.language_id, func.count(CanonicalTranslation.id)
        )
        .filter(CanonicalTranslation.status == CANON_APPROVED)
        .group_by(CanonicalTranslation.language_id)
        .all()
    )
    contrib_by_lang = dict(
        db.session.query(
            Submission.language_id, func.count(func.distinct(Submission.user_id))
        )
        .group_by(Submission.language_id)
        .all()
    )
    sub_by_dialect = dict(
        db.session.query(Submission.dialect_id, func.count(Submission.id))
        .filter(Submission.dialect_id.isnot(None))
        .group_by(Submission.dialect_id)
        .all()
    )
    approved_by_dialect = dict(
        db.session.query(
            CanonicalTranslation.dialect_id, func.count(CanonicalTranslation.id)
        )
        .filter(
            CanonicalTranslation.dialect_id.isnot(None),
            CanonicalTranslation.status == CANON_APPROVED,
        )
        .group_by(CanonicalTranslation.dialect_id)
        .all()
    )

    languages = []
    for lang in Language.query.filter_by(is_active=True).order_by(Language.name).all():
        submissions = sub_by_lang.get(lang.id, 0)
        approved = approved_by_lang.get(lang.id, 0)
        dialects = []
        for dialect in sorted(lang.dialects, key=lambda d: d.name):
            d_submissions = sub_by_dialect.get(dialect.id, 0)
            d_approved = approved_by_dialect.get(dialect.id, 0)
            if d_submissions or d_approved:
                dialects.append(
                    {
                        "id": dialect.id,
                        "name": dialect.name,
                        "submissions": d_submissions,
                        "approved": d_approved,
                    }
                )
        languages.append(
            {
                "id": lang.id,
                "name": lang.name,
                "native_name": lang.native_name,
                "dialect_count": len(lang.dialects),
                "dialects": dialects,
                "submissions": submissions,
                "approved": approved,
                "contributors": contrib_by_lang.get(lang.id, 0),
                "approved_ratio": round(approved / submissions, 3) if submissions else 0.0,
            }
        )
    languages.sort(key=lambda x: x["submissions"], reverse=True)

    top = [
        {
            "contributor": entry["user"].display_name,
            "reputation": entry["reputation"],
            "tier": entry["tier_label"],
            "approved": entry["approved"],
            "submissions": entry["submissions"],
        }
        for entry in recognition.leaderboard(limit=6)
    ]

    totals = {
        "languages": len(languages),
        "languages_with_data": sum(1 for x in languages if x["submissions"] > 0),
        "dialects": Dialect.query.count(),
        "terms": Term.query.count(),
        "submissions": Submission.query.count(),
        "approved_translations": CanonicalTranslation.query.filter_by(
            status=CANON_APPROVED
        ).count(),
        "assessments": Vote.query.count(),
        "contributors": User.query.count(),
        "registered_contributors": User.query.filter_by(is_seed=False).count(),
        "counties": County.query.count(),
    }

    return jsonify(
        {
            "totals": totals,
            "languages": languages,
            "top_contributors": top,
        }
    )


@api_bp.route("/languages")
def languages():
    data = []
    for lang in Language.query.filter_by(is_active=True).order_by(Language.name).all():
        data.append(
            {
                "id": lang.id,
                "name": lang.name,
                "native_name": lang.native_name,
                "iso_code": lang.iso_code,
                "dialects": [
                    {"id": d.id, "name": d.name}
                    for d in sorted(lang.dialects, key=lambda x: x.name)
                ],
            }
        )
    return jsonify({"count": len(data), "languages": data})


@api_bp.route("/counties")
def counties():
    data = [
        {"id": c.id, "code": c.code, "name": c.name, "region": c.region}
        for c in County.query.order_by(County.code).all()
    ]
    return jsonify({"count": len(data), "counties": data})


@api_bp.route("/terms")
def terms():
    category = request.args.get("category")
    query = Term.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    data = [_term_json(t) for t in query.order_by(Term.sort_order).all()]
    return jsonify({"count": len(data), "terms": data})


@api_bp.route("/translations")
def translations():
    query = CanonicalTranslation.query.filter_by(status=CANON_APPROVED)
    lang = request.args.get("language")
    if lang:
        language = Language.query.filter(
            db.func.lower(Language.name) == lang.lower()
        ).first()
        if not language:
            return jsonify({"error": f"Unknown language '{lang}'"}), 404
        query = query.filter_by(language_id=language.id)
    term_slug = request.args.get("term")
    if term_slug:
        term = Term.query.filter_by(slug=term_slug).first()
        if not term:
            return jsonify({"error": f"Unknown term '{term_slug}'"}), 404
        query = query.filter_by(term_id=term.id)
    data = [_translation_json(c) for c in query.all()]
    return jsonify({"count": len(data), "translations": data})


@api_bp.route("/translations/<slug>")
def translations_for_term(slug):
    term = Term.query.filter_by(slug=slug).first()
    if not term:
        return jsonify({"error": f"Unknown term '{slug}'"}), 404
    query = CanonicalTranslation.query.filter_by(
        term_id=term.id, status=CANON_APPROVED
    )
    lang = request.args.get("language")
    if lang:
        language = Language.query.filter(
            db.func.lower(Language.name) == lang.lower()
        ).first()
        if language:
            query = query.filter_by(language_id=language.id)
    data = [_translation_json(c) for c in query.all()]
    return jsonify(
        {"term": _term_json(term), "count": len(data), "translations": data}
    )


@api_bp.route("/leaderboard")
def leaderboard():
    rows = []
    for rank, entry in enumerate(recognition.leaderboard(limit=25), start=1):
        rows.append(
            {
                "rank": rank,
                "contributor": entry["user"].display_name,
                "reputation": entry["reputation"],
                "tier": entry["tier_label"],
                "approved_translations": entry["approved"],
            }
        )
    return jsonify({"count": len(rows), "leaderboard": rows})


@api_bp.route("/token", methods=["POST"])
def token():
    """Issue a short-lived JWT for a registered contributor."""
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user or user.is_seed or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
    }
    token_value = jwt.encode(
        claims, current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
    return jsonify(
        {
            "token": token_value,
            "expires_in": current_app.config["JWT_EXPIRY_HOURS"] * 3600,
        }
    )
