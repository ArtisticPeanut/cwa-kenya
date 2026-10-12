from functools import wraps

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.forms import ReviewForm, TermForm
from app.models import (
    ACTION_FLAG,
    ACTION_REJECT,
    ACTION_REQUEST_REVISION,
    CANON_APPROVED,
    CANON_DISPUTED,
    CANON_NEEDS_REVIEW,
    CanonicalTranslation,
    Dialect,
    Language,
    Review,
    ROLE_ADMIN,
    ROLE_LABELS,
    ROLE_REVIEWER,
    STATUS_APPROVED,
    STATUS_CANDIDATE,
    STATUS_NEEDS_REVIEW,
    STATUS_REJECTED,
    STATUS_SHORTLISTED,
    Submission,
    Term,
    User,
)
from app.services import consensus, recognition
from app.services import exporter, importer

admin_bp = Blueprint("admin", __name__)


def reviewer_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_reviewer:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #

@admin_bp.route("/")
@reviewer_required
def dashboard():
    total_submissions = Submission.query.count()
    status_counts = dict(
        db.session.query(Submission.status, func.count(Submission.id))
        .group_by(Submission.status)
        .all()
    )
    stats = {
        "terms": Term.query.count(),
        "submissions": total_submissions,
        "candidates": status_counts.get(STATUS_CANDIDATE, 0),
        "needs_review": status_counts.get(STATUS_NEEDS_REVIEW, 0),
        "approved_submissions": status_counts.get(STATUS_APPROVED, 0),
        "canonicals": CanonicalTranslation.query.count(),
        "approved_canonicals": CanonicalTranslation.query.filter_by(
            status=CANON_APPROVED
        ).count(),
        "disputed": CanonicalTranslation.query.filter_by(status=CANON_DISPUTED).count(),
        "contributors": User.query.filter_by(is_seed=False).count(),
        "seed_contributors": User.query.filter_by(is_seed=True).count(),
        "reviews": Review.query.count(),
    }
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, recent_reviews=recent_reviews)


# --------------------------------------------------------------------------- #
# Review queue
# --------------------------------------------------------------------------- #

@admin_bp.route("/review")
@reviewer_required
def review_queue():
    language_id = request.args.get("language_id", type=int)
    only_ready = request.args.get("ready") == "1"

    terms = Term.query.filter_by(is_active=True).order_by(Term.sort_order).all()
    queue = []
    for term in terms:
        for summary in consensus.scope_summary_for_term(term):
            if language_id and summary["language"].id != language_id:
                continue
            state = summary["consensus"]["state"]
            if only_ready and state != consensus.CONSENSUS_REACHED:
                continue
            if summary["count"] == 0:
                continue
            queue.append(
                {
                    "term": term,
                    "language": summary["language"],
                    "dialect": summary["dialect"],
                    "count": summary["count"],
                    "consensus": summary["consensus"],
                    "canonical": consensus.canonical_for(
                        term.id,
                        summary["language"].id,
                        summary["dialect"].id if summary["dialect"] else None,
                    ),
                }
            )

    order = {
        consensus.CONSENSUS_REACHED: 0,
        consensus.CONSENSUS_AMBIGUOUS: 1,
        consensus.CONSENSUS_INSUFFICIENT: 2,
        consensus.CONSENSUS_EMPTY: 3,
    }
    queue.sort(key=lambda r: (order.get(r["consensus"]["state"], 9), r["term"].sort_order))

    return render_template(
        "admin/review_queue.html",
        queue=queue,
        languages=Language.query.order_by(Language.name).all(),
        language_id=language_id,
        only_ready=only_ready,
        consensus_labels=consensus.CONSENSUS_LABELS,
    )


@admin_bp.route("/review/<int:term_id>/<int:language_id>")
@reviewer_required
def compare(term_id, language_id):
    term = db.session.get(Term, term_id) or abort(404)
    language = db.session.get(Language, language_id) or abort(404)
    dialect_id = request.args.get("dialect_id", type=int)
    dialect = db.session.get(Dialect, dialect_id) if dialect_id else None

    ranked = consensus.rank_candidates(term_id, language_id, dialect_id)
    scope = consensus.scope_consensus(term_id, language_id, dialect_id)
    canonical = consensus.canonical_for(term_id, language_id, dialect_id)
    form = ReviewForm()
    return render_template(
        "admin/compare.html",
        term=term,
        language=language,
        dialect=dialect,
        ranked=ranked,
        scope=scope,
        canonical=canonical,
        form=form,
        progress_lines=consensus.CONSENSUS_LABELS,
        languages=Language.query.order_by(Language.name).all(),
        dialects=Dialect.query.order_by(Dialect.name).all(),
    )


@admin_bp.route("/review/submission/<int:submission_id>/reclassify", methods=["POST"])
@reviewer_required
def reclassify(submission_id):
    submission = db.session.get(Submission, submission_id) or abort(404)
    language = db.session.get(Language, request.form.get("language_id", type=int))
    dialect_id = request.form.get("dialect_id", type=int)
    dialect = db.session.get(Dialect, dialect_id) if dialect_id else None
    if not language:
        flash("Choose a language before reclassifying.", "danger")
    else:
        submission.language_id = language.id
        submission.dialect_id = dialect.id if dialect else None
        submission.updated_at = consensus.utcnow()
        db.session.commit()
        flash(
            f"Submission reclassified to {language.name}"
            f"{' · ' + dialect.name if dialect else ''}.",
            "success",
        )
    return redirect(request.referrer or url_for("admin.review_queue"))


@admin_bp.route("/review/submission/<int:submission_id>", methods=["POST"])
@reviewer_required
def decide(submission_id):
    submission = db.session.get(Submission, submission_id) or abort(404)
    action = request.form.get("action")
    note = request.form.get("note")
    mapping = {
        ACTION_REJECT: ACTION_REJECT,
        ACTION_REQUEST_REVISION: ACTION_REQUEST_REVISION,
        ACTION_FLAG: ACTION_FLAG,
    }
    if action not in mapping:
        flash("Unknown review action.", "danger")
        return redirect(request.referrer or url_for("admin.review_queue"))
    consensus.review_submission(current_user, submission, action, note)
    db.session.commit()
    flash(f"Submission marked: {action.replace('_', ' ')}.", "success")
    return redirect(request.referrer or url_for("admin.review_queue"))


@admin_bp.route("/review/approve/<int:submission_id>", methods=["POST"])
@reviewer_required
def approve(submission_id):
    submission = db.session.get(Submission, submission_id) or abort(404)
    note = request.form.get("note")
    definition = request.form.get("definition") or None
    context = request.form.get("context") or None
    consensus.approve_canonical(
        submission.term, submission.language, submission.dialect, submission,
        current_user, definition=definition, context=context, note=note,
    )
    db.session.commit()
    flash(
        f"Approved canonical translation for {submission.term.english_name} "
        f"({submission.language.name}).",
        "success",
    )
    return redirect(request.referrer or url_for("admin.review_queue"))


# --------------------------------------------------------------------------- #
# Canonical management
# --------------------------------------------------------------------------- #

@admin_bp.route("/canonical")
@reviewer_required
def canonical_list():
    language_id = request.args.get("language_id", type=int)
    status = request.args.get("status")
    query = CanonicalTranslation.query
    if language_id:
        query = query.filter_by(language_id=language_id)
    if status:
        query = query.filter_by(status=status)
    canonicals = query.join(Term).order_by(Term.sort_order, CanonicalTranslation.language_id).all()
    return render_template(
        "admin/canonical_list.html",
        canonicals=canonicals,
        languages=Language.query.order_by(Language.name).all(),
        language_id=language_id,
        status=status,
        status_choices=[
            (CANON_APPROVED, "Approved"),
            (CANON_NEEDS_REVIEW, "Needs review"),
            (CANON_DISPUTED, "Disputed"),
        ],
    )


@admin_bp.route("/canonical/<int:canonical_id>", methods=["GET", "POST"])
@reviewer_required
def canonical_detail(canonical_id):
    canon = db.session.get(CanonicalTranslation, canonical_id) or abort(404)
    if request.method == "POST":
        new_status = request.form.get("status")
        note = request.form.get("note")
        if new_status in (CANON_APPROVED, CANON_DISPUTED, CANON_NEEDS_REVIEW):
            consensus.set_canonical_status(canon, new_status, current_user, note)
            db.session.commit()
            flash("Canonical status updated.", "success")
            return redirect(url_for("admin.canonical_detail", canonical_id=canon.id))
    return render_template("admin/canonical_detail.html", canon=canon)


# --------------------------------------------------------------------------- #
# Terms
# --------------------------------------------------------------------------- #

@admin_bp.route("/terms")
@reviewer_required
def terms():
    rows = Term.query.order_by(Term.sort_order).all()
    return render_template("admin/terms.html", terms=rows)


@admin_bp.route("/terms/new", methods=["GET", "POST"])
@admin_required
def term_new():
    form = TermForm()
    if form.validate_on_submit():
        slug = _slugify(form.english_name.data)
        if Term.query.filter_by(slug=slug).first():
            flash("A term with a similar name already exists.", "danger")
        else:
            order = (db.session.query(func.max(Term.sort_order)).scalar() or 0) + 1
            db.session.add(
                Term(
                    slug=slug,
                    category=form.category.data,
                    sort_order=order,
                    english_name=form.english_name.data.strip(),
                    english_definition=form.english_definition.data.strip(),
                    swahili_name=form.swahili_name.data or None,
                    swahili_definition=form.swahili_definition.data or None,
                )
            )
            db.session.commit()
            flash("Term created.", "success")
            return redirect(url_for("admin.terms"))
    return render_template("admin/term_form.html", form=form, term=None)


@admin_bp.route("/terms/<int:term_id>/edit", methods=["GET", "POST"])
@admin_required
def term_edit(term_id):
    term = db.session.get(Term, term_id) or abort(404)
    form = TermForm(obj=term)
    if form.validate_on_submit():
        term.english_name = form.english_name.data.strip()
        term.category = form.category.data
        term.english_definition = form.english_definition.data.strip()
        term.swahili_name = form.swahili_name.data or None
        term.swahili_definition = form.swahili_definition.data or None
        db.session.commit()
        flash("Term updated.", "success")
        return redirect(url_for("admin.terms"))
    return render_template("admin/term_form.html", form=form, term=term)


def _slugify(value):
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "term"


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #

@admin_bp.route("/users")
@admin_required
def users():
    rows = User.query.order_by(User.is_seed.desc(), User.created_at.desc()).all()
    return render_template("admin/users.html", users=rows, role_labels=ROLE_LABELS)


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def set_role(user_id):
    user = db.session.get(User, user_id) or abort(404)
    role = request.form.get("role")
    if role not in (ROLE_LABELS):
        flash("Unknown role.", "danger")
    elif user.id == current_user.id and role != ROLE_ADMIN:
        flash("You cannot remove your own administrator role.", "warning")
    else:
        user.role = role
        db.session.commit()
        flash(f"{user.display_name} is now a {ROLE_LABELS[role]}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash("User status updated.", "success")
    return redirect(url_for("admin.users"))


# --------------------------------------------------------------------------- #
# Data: import & export
# --------------------------------------------------------------------------- #

@admin_bp.route("/data")
@admin_required
def data():
    return render_template(
        "admin/data.html",
        approved=CanonicalTranslation.query.count(),
        submissions=Submission.query.count(),
    )


@admin_bp.route("/data/import", methods=["POST"])
@admin_required
def run_import():
    path = request.form.get("csv_path", "").strip()
    if not path:
        flash("Provide the path to the responses CSV.", "danger")
        return redirect(url_for("admin.data"))
    try:
        stats = importer.import_csv(path)
        flash(
            f"Imported {stats['submissions']} submissions from "
            f"{stats['rows']} rows ({stats['skipped']} duplicates skipped).",
            "success",
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f"Import failed: {exc}", "danger")
    return redirect(url_for("admin.data"))


@admin_bp.route("/export/translations.json")
@reviewer_required
def export_json():
    include_unapproved = request.args.get("all") == "1"
    payload = exporter.to_json(include_unapproved=include_unapproved)
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=cwa_translations.json"},
    )


@admin_bp.route("/export/translations.csv")
@reviewer_required
def export_csv():
    include_unapproved = request.args.get("all") == "1"
    payload = exporter.to_csv(include_unapproved=include_unapproved)
    return Response(
        payload,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cwa_translations.csv"},
    )


@admin_bp.route("/export/submissions.csv")
@reviewer_required
def export_submissions():
    payload = exporter.to_submissions_csv()
    return Response(
        payload,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cwa_submissions.csv"},
    )
