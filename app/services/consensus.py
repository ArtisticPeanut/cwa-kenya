"""Community verification, consensus and canonical approval logic."""

import json
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import (
    ACTION_APPROVE,
    ACTION_FLAG,
    ACTION_REJECT,
    ACTION_REQUEST_REVISION,
    ACTION_REPLACE,
    CANON_APPROVED,
    CANON_DISPUTED,
    CANON_NEEDS_REVIEW,
    CanonicalRevision,
    CanonicalTranslation,
    Review,
    STATUS_APPROVED,
    STATUS_CANDIDATE,
    STATUS_NEEDS_REVIEW,
    STATUS_REJECTED,
    STATUS_SHORTLISTED,
    Submission,
    VOTE_OPPOSE,
    VOTE_SUPPORT,
    Vote,
)
from app.services import recognition

# Consensus states
CONSENSUS_REACHED = "reached"
CONSENSUS_AMBIGUOUS = "ambiguous"
CONSENSUS_INSUFFICIENT = "insufficient"
CONSENSUS_EMPTY = "empty"
CONSENSUS_LABELS = {
    CONSENSUS_REACHED: "Consensus reached",
    CONSENSUS_AMBIGUOUS: "Competing interpretations",
    CONSENSUS_INSUFFICIENT: "Not enough participation",
    CONSENSUS_EMPTY: "No candidates yet",
}


def utcnow():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Candidates and tallies
# --------------------------------------------------------------------------- #

def candidates_for(term_id, language_id, dialect_id=None, include_rejected=False):
    query = Submission.query.filter_by(term_id=term_id, language_id=language_id)
    if dialect_id:
        query = query.filter_by(dialect_id=dialect_id)
    else:
        query = query.filter(Submission.dialect_id.is_(None))
    if not include_rejected:
        query = query.filter(Submission.status != STATUS_REJECTED)
    return query.order_by(Submission.created_at.asc()).all()


def tally(submission):
    support = oppose = 0
    for vote in submission.votes:
        if vote.value == VOTE_SUPPORT:
            support += 1
        elif vote.value == VOTE_OPPOSE:
            oppose += 1
    total = support + oppose
    return {
        "support": support,
        "oppose": oppose,
        "total": total,
        "ratio": (support / total) if total else 0.0,
    }


def rank_candidates(term_id, language_id, dialect_id=None, include_rejected=False):
    """Return candidates enriched with vote tallies, ordered by community support."""
    candidates = candidates_for(
        term_id, language_id, dialect_id, include_rejected=include_rejected
    )
    ranked = []
    for sub in candidates:
        stats = tally(sub)
        ranked.append({"submission": sub, "stats": stats})

    def sort_key(item):
        s = item["stats"]
        return (s["support"], s["ratio"], -item["submission"].id)

    ranked.sort(key=sort_key, reverse=True)

    if ranked:
        lead = ranked[0]["stats"]["support"]
        for i, item in enumerate(ranked):
            item["is_leader"] = i == 0 and item["stats"]["support"] > 0
            others = [r["stats"]["support"] for r in ranked if r is not item]
            item["lead_margin"] = (lead - max(others)) if others else lead
    return ranked


def scope_consensus(term_id, language_id, dialect_id=None):
    """Evaluate consensus for a single (term, language, dialect) scope."""
    ranked = rank_candidates(term_id, language_id, dialect_id)
    if not ranked:
        return {"state": CONSENSUS_EMPTY, "ranked": [], "leader": None,
                "runner_up": None}

    leader = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    min_votes = current_app.config["MIN_VOTES_FOR_CONSENSUS"]
    ratio_needed = current_app.config["CONSENSUS_RATIO"]
    margin_needed = current_app.config["AMBIGUITY_MARGIN"]

    state = CONSENSUS_INSUFFICIENT
    if leader["stats"]["total"] >= min_votes and leader["stats"]["ratio"] >= ratio_needed:
        if runner_up and runner_up["stats"]["total"] > 0:
            total_votes = leader["stats"]["total"]
            gap = leader["stats"]["support"] - runner_up["stats"]["support"]
            if total_votes and (gap / total_votes) < margin_needed:
                state = CONSENSUS_AMBIGUOUS
            else:
                state = CONSENSUS_REACHED
        else:
            state = CONSENSUS_REACHED
    elif leader["stats"]["total"] > 0 and leader["stats"]["total"] < min_votes:
        state = CONSENSUS_INSUFFICIENT

    return {
        "state": state,
        "label": CONSENSUS_LABELS[state],
        "ranked": ranked,
        "leader": leader if state == CONSENSUS_REACHED else None,
        "runner_up": runner_up,
    }


def scope_summary_for_term(term):
    """Group scopes (language/dialect) that have at least one candidate."""
    rows = (
        db.session.query(
            Submission.language_id,
            Submission.dialect_id,
            func.count(Submission.id),
        )
        .filter(Submission.term_id == term.id)
        .group_by(Submission.language_id, Submission.dialect_id)
        .all()
    )
    from app.models import Dialect, Language

    summaries = []
    for language_id, dialect_id, count in rows:
        language = db.session.get(Language, language_id)
        dialect = db.session.get(Dialect, dialect_id) if dialect_id else None
        consensus = scope_consensus(term.id, language_id, dialect_id)
        summaries.append(
            {
                "language": language,
                "dialect": dialect,
                "count": count,
                "consensus": consensus,
            }
        )
    return summaries


# --------------------------------------------------------------------------- #
# Submissions & voting
# --------------------------------------------------------------------------- #

def create_submission(user, term, language, dialect, text, usage_note=None,
                      example=None, is_seed=False, consent_public=False):
    text = (text or "").strip()
    if not text:
        raise ValueError("Translation text cannot be empty.")
    sub = Submission(
        term_id=term.id,
        language_id=language.id,
        dialect_id=dialect.id if dialect else None,
        user_id=user.id,
        text=text,
        usage_note=(usage_note or "").strip() or None,
        example=(example or "").strip() or None,
        status=STATUS_CANDIDATE,
        is_seed=is_seed,
        consent_public=consent_public,
    )
    db.session.add(sub)
    db.session.flush()

    if not is_seed:
        recognition.record_contribution(
            user, "submit_translation", ref_type="submission", ref_id=sub.id
        )
        if sub.usage_note or sub.example:
            recognition.record_contribution(
                user, "add_context",
                ref_type="submission", ref_id=sub.id,
                quality_points=recognition.QUALITY_POINTS["context_provided"],
            )
        recognition.evaluate_milestones(user)
    return sub


def cast_vote(user, submission, value):
    if user.id == submission.user_id:
        raise ValueError("You cannot vote on your own submission.")
    if value not in (VOTE_SUPPORT, VOTE_OPPOSE):
        raise ValueError("Invalid vote value.")
    vote = Vote.query.filter_by(
        submission_id=submission.id, user_id=user.id
    ).first()
    is_new = vote is None
    if vote is None:
        vote = Vote(submission_id=submission.id, user_id=user.id, value=value)
        db.session.add(vote)
    else:
        vote.value = value
    db.session.flush()
    recognition.recompute_submission_quality(submission)
    if is_new:
        recognition.record_contribution(
            user, "cast_vote", ref_type="submission", ref_id=submission.id
        )
        recognition.evaluate_milestones(user)
    return vote


# --------------------------------------------------------------------------- #
# Review decisions
# --------------------------------------------------------------------------- #

def review_submission(reviewer, submission, action, note=None):
    review = Review(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        action=action,
        note=(note or "").strip() or None,
    )
    db.session.add(review)

    if action == ACTION_APPROVE:
        submission.status = STATUS_APPROVED
    elif action == ACTION_REJECT:
        submission.status = STATUS_REJECTED
    elif action == ACTION_REQUEST_REVISION:
        submission.status = STATUS_SHORTLISTED
    elif action == ACTION_FLAG:
        submission.status = STATUS_NEEDS_REVIEW

    db.session.flush()
    recognition.record_contribution(
        reviewer, "review_decision", ref_type="submission", ref_id=submission.id
    )
    recognition.evaluate_milestones(reviewer)
    return review


def set_canonical_status(canonical, status, reviewer, note=None):
    canonical.status = status
    canonical.updated_at = utcnow()
    db.session.add(
        CanonicalRevision(
            canonical_id=canonical.id,
            revision_no=canonical.revision_no,
            change_type="status",
            snapshot=_snapshot(canonical),
            note=note,
            changed_by=reviewer.id if reviewer else None,
        )
    )
    db.session.flush()
    return canonical


def approve_canonical(term, language, dialect, submission, reviewer,
                      definition=None, context=None, note=None):
    """Approve a submission as the canonical translation for its scope.

    Preserves a full revision history and keeps competing interpretations
    available when they still have community support.
    """
    dialect_id = dialect.id if dialect else None
    canonical = CanonicalTranslation.query.filter_by(
        term_id=term.id, language_id=language.id, dialect_id=dialect_id
    ).first()

    now = utcnow()
    if canonical is None:
        canonical = CanonicalTranslation(
            term_id=term.id,
            language_id=language.id,
            dialect_id=dialect_id,
            submission_id=submission.id,
            text=submission.text,
            definition=definition if definition is not None else submission.usage_note,
            context=context if context is not None else submission.example,
            status=CANON_APPROVED,
            revision_no=1,
            approved_by=reviewer.id if reviewer else None,
            approved_at=now,
        )
        db.session.add(canonical)
        db.session.flush()
        change_type = "create"
    else:
        canonical.revision_no += 1
        canonical.submission_id = submission.id
        canonical.text = submission.text
        canonical.definition = (
            definition if definition is not None else submission.usage_note
        )
        canonical.context = context if context is not None else submission.example
        canonical.status = CANON_APPROVED
        canonical.approved_by = reviewer.id if reviewer else None
        canonical.approved_at = now
        canonical.updated_at = now
        change_type = "replace"

    db.session.add(
        CanonicalRevision(
            canonical_id=canonical.id,
            revision_no=canonical.revision_no,
            change_type=change_type,
            snapshot=_snapshot(canonical),
            note=note,
            changed_by=reviewer.id if reviewer else None,
        )
    )

    submission.status = STATUS_APPROVED
    review = Review(
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        action=ACTION_REPLACE if change_type == "replace" else ACTION_APPROVE,
        note=note,
    )
    db.session.add(review)
    db.session.flush()

    # Flag competing candidates that were not chosen, if any remain supported.
    for other in candidates_for(term.id, language.id, dialect_id):
        if other.id != submission.id and tally(other)["support"] > 0:
            other.status = STATUS_NEEDS_REVIEW

    recognition.record_contribution(
        reviewer, "review_decision", ref_type="submission", ref_id=submission.id
    )
    recognition.record_contribution(
        submission.user, "translation_approved",
        ref_type="submission", ref_id=submission.id,
    )
    recognition.evaluate_milestones(reviewer)
    if submission.user:
        recognition.evaluate_milestones(submission.user)
    return canonical


def _snapshot(canonical):
    return json.dumps(
        {
            "text": canonical.text,
            "definition": canonical.definition,
            "context": canonical.context,
            "status": canonical.status,
            "submission_id": canonical.submission_id,
            "revision_no": canonical.revision_no,
        },
        ensure_ascii=False,
    )


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #

def canonical_for(term_id, language_id, dialect_id=None):
    return CanonicalTranslation.query.filter_by(
        term_id=term_id, language_id=language_id, dialect_id=dialect_id
    ).first()


def canonical_map_for_term(term):
    out = {}
    for canon in term.canonicals:
        if canon.status == CANON_APPROVED:
            out[(canon.language_id, canon.dialect_id)] = canon
    return out
