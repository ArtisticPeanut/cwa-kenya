import random

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import SubmissionForm
from app.models import (
    CATEGORY_GLOSSARY,
    CATEGORY_MESSAGE,
    CANON_APPROVED,
    CanonicalTranslation,
    County,
    Dialect,
    Language,
    STATUS_REJECTED,
    Submission,
    Term,
    VOTE_OPPOSE,
    VOTE_SUPPORT,
)
from app.services import consensus, recognition
from app.services.exporter import approved_records
from app.services.importer import LANGUAGE_ALIASES

main_bp = Blueprint("main", __name__)

SESSION_LANG = "selected_language_id"
SESSION_DIALECT = "selected_dialect_id"


# --------------------------------------------------------------------------- #
# Session helpers
# --------------------------------------------------------------------------- #

def selected_language():
    lang_id = session.get(SESSION_LANG)
    if lang_id:
        lang = db.session.get(Language, lang_id)
        if lang:
            return lang
    if current_user.is_authenticated and current_user.preferred_language:
        return current_user.preferred_language
    return None


def selected_dialect():
    dialect_id = session.get(SESSION_DIALECT)
    if dialect_id:
        dialect = db.session.get(Dialect, dialect_id)
        if dialect:
            return dialect
    if current_user.is_authenticated and current_user.preferred_dialect:
        return current_user.preferred_dialect
    return None


# --------------------------------------------------------------------------- #
# Home & language selection
# --------------------------------------------------------------------------- #

@main_bp.route("/")
def home():
    stats = {
        "languages": Language.query.count(),
        "terms": Term.query.count(),
        "submissions": Submission.query.count(),
        "approved": CanonicalTranslation.query.count(),
        "counties": County.query.count(),
    }
    return render_template(
        "main/home.html",
        stats=stats,
        languages=Language.query.order_by(Language.name).all(),
        counties=County.query.order_by(County.name).all(),
    )


@main_bp.route("/languages", methods=["GET", "POST"])
def select_language():
    counties = County.query.order_by(County.name).all()
    languages = Language.query.filter_by(is_active=True).order_by(Language.name).all()
    selected_county = None
    suggested = []
    if request.method == "POST":
        county_id = request.form.get("county_id", type=int)
        language_id = request.form.get("language_id", type=int)
        dialect_id = request.form.get("dialect_id", type=int)

        if county_id:
            selected_county = db.session.get(County, county_id)
        language = db.session.get(Language, language_id) if language_id else None
        if language:
            session[SESSION_LANG] = language.id
            session[SESSION_DIALECT] = dialect_id or None
            flash(f"Language set to {language.name}.", "success")
            return redirect(url_for("main.tasks"))

    if selected_county:
        suggested = selected_county.languages

    all_dialects = Dialect.query.order_by(Dialect.name).all()
    return render_template(
        "main/select_language.html",
        counties=counties,
        languages=languages,
        selected_county=selected_county,
        suggested=suggested,
        all_dialects=all_dialects,
    )


@main_bp.route("/languages/set/<int:language_id>")
def set_language(language_id):
    language = db.session.get(Language, language_id) or abort(404)
    session[SESSION_LANG] = language.id
    dialect_id = request.args.get("dialect_id", type=int)
    session[SESSION_DIALECT] = dialect_id or None
    flash(f"Now viewing tasks in {language.name}.", "success")
    return redirect(url_for("main.tasks"))


@main_bp.route("/languages/clear")
def clear_language():
    session.pop(SESSION_LANG, None)
    session.pop(SESSION_DIALECT, None)
    flash("Language selection cleared.", "info")
    return redirect(url_for("main.tasks"))


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #

@main_bp.route("/tasks")
def tasks():
    language = selected_language()
    dialect = selected_dialect()
    terms = Term.query.filter_by(is_active=True).order_by(Term.sort_order).all()

    rows = []
    for term in terms:
        dialect_id = dialect.id if dialect else None
        scope = (
            consensus.scope_consensus(term.id, language.id, dialect_id)
            if language else None
        )
        ranked = scope["ranked"] if scope else []
        canonical = (
            consensus.canonical_for(term.id, language.id, dialect_id)
            if language else None
        )
        rows.append(
            {
                "term": term,
                "candidates": len(ranked),
                "canonical": canonical,
                "consensus": scope["state"] if scope else None,
            }
        )

    done = sum(1 for r in rows if r["canonical"])
    return render_template(
        "main/tasks.html",
        language=language,
        dialect=dialect,
        rows=rows,
        done=done,
        total=len(rows),
    )


@main_bp.route("/tasks/<slug>", methods=["GET"])
def task_detail(slug):
    term = Term.query.filter_by(slug=slug).first() or abort(404)
    language = selected_language()
    dialect = selected_dialect()
    form = SubmissionForm()
    form.language_id.choices = [
        (l.id, l.name) for l in Language.query.order_by(Language.name).all()
    ]
    form.dialect_id.choices = [(0, "— None / community-wide —")] + [
        (d.id, f"{d.name} ({d.language.name})")
        for d in Dialect.query.order_by(Dialect.name).all()
    ]
    dialect_id = dialect.id if dialect else None
    if language:
        form.language_id.data = language.id
        form.dialect_id.data = dialect_id or 0

    ranked = (
        consensus.rank_candidates(term.id, language.id, dialect_id)
        if language else []
    )
    scope = (
        consensus.scope_consensus(term.id, language.id, dialect_id)
        if language else None
    )
    canonical = (
        consensus.canonical_for(term.id, language.id, dialect_id)
        if language else None
    )
    my_votes = {}
    if current_user.is_authenticated:
        for sub in Submission.query.filter_by(
            term_id=term.id, language_id=language.id if language else 0
        ).all():
            vote = next((v for v in sub.votes if v.user_id == current_user.id), None)
            if vote:
                my_votes[sub.id] = vote.value

    return render_template(
        "main/task_detail.html",
        term=term,
        language=language,
        dialect=dialect,
        form=form,
        ranked=ranked,
        scope=scope,
        canonical=canonical,
        my_votes=my_votes,
    )


@main_bp.route("/tasks/<slug>/submit", methods=["POST"])
@login_required
def submit_translation(slug):
    term = Term.query.filter_by(slug=slug).first() or abort(404)
    form = SubmissionForm()
    form.language_id.choices = [
        (l.id, l.name) for l in Language.query.order_by(Language.name).all()
    ]
    form.dialect_id.choices = [(0, "— None / community-wide —")] + [
        (d.id, f"{d.name} ({d.language.name})")
        for d in Dialect.query.order_by(Dialect.name).all()
    ]
    if form.validate_on_submit():
        language = db.session.get(Language, form.language_id.data)
        dialect = db.session.get(Dialect, form.dialect_id.data) if form.dialect_id.data else None
        if not language:
            flash("Please choose a language.", "danger")
            return redirect(url_for("main.task_detail", slug=slug))
        try:
            consensus.create_submission(
                current_user, term, language, dialect,
                form.text.data, form.usage_note.data, form.example.data,
                consent_public=True,
            )
            db.session.commit()
            flash("Thank you! Your translation has been submitted for community review.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    else:
        flash("Please provide a translation of at least 2 characters.", "danger")
    return redirect(url_for("main.task_detail", slug=slug))


@main_bp.route("/submissions/<int:submission_id>/vote", methods=["POST"])
@login_required
def vote(submission_id):
    submission = db.session.get(Submission, submission_id) or abort(404)
    value = request.form.get("value")
    if value not in (VOTE_SUPPORT, VOTE_OPPOSE):
        flash("Invalid assessment.", "danger")
        return redirect(request.referrer or url_for("main.tasks"))
    try:
        consensus.cast_vote(current_user, submission, value)
        db.session.commit()
        flash("Your assessment has been recorded.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "warning")
    return redirect(request.referrer or url_for("main.tasks"))


# --------------------------------------------------------------------------- #
# Browse / glossary
# --------------------------------------------------------------------------- #

@main_bp.route("/browse")
def browse():
    category = request.args.get("category")
    language_id = request.args.get("language_id", type=int)
    query = Term.query.filter_by(is_active=True)
    if category in (CATEGORY_GLOSSARY, CATEGORY_MESSAGE):
        query = query.filter_by(category=category)
    terms = query.order_by(Term.sort_order).all()

    language = db.session.get(Language, language_id) if language_id else None
    rows = []
    for term in terms:
        canonicals = [
            c for c in term.canonicals if c.status == CANON_APPROVED
        ]
        if language:
            canonicals = [c for c in canonicals if c.language_id == language.id]
        rows.append({"term": term, "canonicals": canonicals})

    return render_template(
        "main/browse.html",
        rows=rows,
        category=category,
        language=language,
        languages=Language.query.order_by(Language.name).all(),
    )


@main_bp.route("/terms/<slug>")
def term_public(slug):
    term = Term.query.filter_by(slug=slug).first() or abort(404)
    canonicals = [c for c in term.canonicals if c.status == CANON_APPROVED]
    canonicals.sort(key=lambda c: (c.language.name, c.dialect.name if c.dialect else ""))
    return render_template("main/term_public.html", term=term, canonicals=canonicals)


# --------------------------------------------------------------------------- #
# Contributors
# --------------------------------------------------------------------------- #

@main_bp.route("/leaderboard")
def leaderboard():
    return render_template("main/leaderboard.html", rows=recognition.leaderboard())


@main_bp.route("/me")
@login_required
def my_contributions():
    submissions = (
        Submission.query.filter_by(user_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    rank = recognition.rank_for_user(current_user)
    milestones = recognition.milestones_status(current_user)
    return render_template(
        "main/profile.html",
        submissions=submissions,
        rank=rank,
        milestones=milestones,
    )


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/learn")
def learn():
    return render_template("main/learn.html")


def _translation_pool(language_id):
    """Best available translation text per term for one language.

    Prefers community-verified canonicals; otherwise falls back to the
    leading *consented* community sample. This keeps the quiz honest: it never
    uses a sample that was not shared for public awareness use.
    """
    pool = {}
    for canon in CanonicalTranslation.query.filter_by(
        language_id=language_id, status=CANON_APPROVED
    ).all():
        pool[canon.term_id] = {"text": canon.text, "term": canon.term, "verified": True}

    subs = (
        Submission.query.filter_by(language_id=language_id, consent_public=True)
        .filter(Submission.status != STATUS_REJECTED)
        .all()
    )
    alias_ids = {
        alias: next((l.id for l in Language.query.filter_by(name=name)), None)
        for alias, name in LANGUAGE_ALIASES.items()
    }
    by_term = {}
    for sub in subs:
        # Guard against mis-tagged rows: if a sample's dialect names a
        # *different* language (e.g. a Kamba/Kisii sample filed under
        # Kiswahili), it does not belong in this language's quiz.
        if sub.dialect_id and sub.dialect:
            implied = alias_ids.get(sub.dialect.name.strip().casefold())
            if implied and implied != sub.language_id:
                continue
        by_term.setdefault(sub.term_id, []).append(sub)
    for term_id, items in by_term.items():
        if term_id in pool:
            continue
        items.sort(key=lambda s: (s.support_count, -s.id), reverse=True)
        best = items[0]
        pool[term_id] = {"text": best.text, "term": best.term, "verified": False}
    return pool


def _language_from_request():
    """Resolve the ?language= / ?language_id= argument used by learner routes."""
    name = request.args.get("language")
    if name:
        language = Language.query.filter(
            db.func.lower(Language.name) == name.strip().lower()
        ).first()
        if language:
            return language
    lang_id = request.args.get("language_id", type=int)
    if lang_id is not None:
        return db.session.get(Language, lang_id)
    return None


@main_bp.route("/learn/quiz")
def learn_quiz():
    """Serve a single match-the-word question for Mimo's quiz."""
    language = _language_from_request()
    if language is None:
        return jsonify({"available": False, "reason": "unknown_language"}), 404

    pool = _translation_pool(language.id)
    entries = [
        {"text": v["text"], "term": v["term"], "verified": v["verified"]}
        for v in pool.values() if v["text"] and v["text"].strip()
    ]
    if len(entries) < 3:
        return jsonify(
            {
                "available": False,
                "language": language.name,
                "reason": "not_enough_words",
                "have": len(entries),
            }
        )

    random.shuffle(entries)
    correct = entries[0]
    options = [correct["text"]]
    for entry in entries[1:]:
        if entry["text"] not in options:
            options.append(entry["text"])
        if len(options) == 4:
            break
    random.shuffle(options)

    return jsonify(
        {
            "available": True,
            "language": language.name,
            "question": {
                "term": correct["term"].english_name,
                "term_slug": correct["term"].slug,
                "category": correct["term"].category,
                "definition": correct["term"].english_definition,
                "swahili_name": correct["term"].swahili_name,
                "options": options,
                "answer_index": options.index(correct["text"]),
                "verified": correct["verified"],
            },
            "pool_size": len(entries),
        }
    )


@main_bp.route("/learn/word")
def learn_word():
    """Serve one consented word/tip for Mimo's chat, in the chosen language."""
    language = _language_from_request()
    if language is None:
        return jsonify({"available": False, "reason": "unknown_language"}), 404

    category = (request.args.get("category") or "").strip().lower()
    exclude = {s for s in (request.args.get("exclude") or "").split(",") if s}
    entries = [
        value
        for value in _translation_pool(language.id).values()
        if value["text"].strip()
        and (not category or value["term"].category == category)
        and value["term"].slug not in exclude
    ]
    if not entries:
        return jsonify(
            {
                "available": False,
                "language": language.name,
                "reason": "not_enough_words",
            }
        )

    choice = random.choice(entries)
    term = choice["term"]
    return jsonify(
        {
            "available": True,
            "language": language.name,
            "word": {
                "term": term.english_name,
                "slug": term.slug,
                "category": term.category,
                "definition": term.english_definition or "",
                "swahili_name": term.swahili_name,
                "translation": choice["text"],
                "verified": choice["verified"],
            },
        }
    )


@main_bp.route("/downloads")
def downloads():
    languages = Language.query.order_by(Language.name).all()
    return render_template(
        "main/downloads.html",
        languages=languages,
        count=len(approved_records()),
    )


@main_bp.route("/downloads/translations.json")
def download_json():
    from flask import Response

    return Response(
        approved_records_json(),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=cwa_translations.json"},
    )


@main_bp.route("/downloads/translations.csv")
def download_csv():
    from flask import Response
    from app.services.exporter import to_csv

    return Response(
        to_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cwa_translations.csv"},
    )


def approved_records_json():
    from app.services.exporter import to_json

    return to_json()
