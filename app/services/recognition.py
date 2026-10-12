"""Contributor recognition: points, milestones and ranking.

The goal is to reward demonstrated quality (approved translations, useful
context, constructive reviews) rather than raw activity or popularity.
"""

from sqlalchemy import func, or_

from app.extensions import db
from app.models import (
    Contribution,
    Milestone,
    Review,
    STATUS_APPROVED,
    Submission,
    User,
    UserMilestone,
    VOTE_SUPPORT,
    Vote,
)

# Points awarded for activity.
POINTS = {
    "submit_translation": 2,
    "add_context": 3,
    "cast_vote": 1,
    "review_decision": 3,
    "translation_approved": 0,
}

# Quality points awarded for durable, verified value.
QUALITY_POINTS = {
    "translation_approved": 10,
    "context_provided": 3,
    "review_decision": 2,
}

# Ranking tiers: (code, label, min_reputation)
TIERS = [
    ("new", "New contributor", 0),
    ("contributor", "Contributor", 20),
    ("trusted", "Trusted contributor", 100),
    ("expert", "Language expert", 250),
    ("master", "Master translator", 500),
]
TIER_LABELS = {code: label for code, label, _ in TIERS}


# --------------------------------------------------------------------------- #
# Contribution ledger
# --------------------------------------------------------------------------- #

def record_contribution(user, action, ref_type=None, ref_id=None,
                        points=None, quality_points=None):
    if user is None:
        return None
    entry = Contribution(
        user_id=user.id,
        action=action,
        ref_type=ref_type,
        ref_id=ref_id,
        points=POINTS.get(action, 0) if points is None else points,
        quality_points=(
            QUALITY_POINTS.get(action, 0) if quality_points is None
            else quality_points
        ),
    )
    db.session.add(entry)
    db.session.flush()
    return entry


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def metrics_for_user(user):
    submissions = Submission.query.filter_by(user_id=user.id)
    total_submissions = submissions.count()
    approved = submissions.filter_by(status=STATUS_APPROVED).count()
    context_submissions = submissions.filter(
        or_(Submission.usage_note.isnot(None), Submission.example.isnot(None))
    ).count()
    languages = (
        db.session.query(func.count(func.distinct(Submission.language_id)))
        .filter(Submission.user_id == user.id)
        .scalar()
        or 0
    )
    reviews = Review.query.filter_by(reviewer_id=user.id).count()
    support_received = (
        db.session.query(func.count(Vote.id))
        .join(Submission, Vote.submission_id == Submission.id)
        .filter(Submission.user_id == user.id, Vote.value == VOTE_SUPPORT)
        .scalar()
        or 0
    )
    votes_cast = Vote.query.filter_by(user_id=user.id).count()

    activity = (
        db.session.query(func.coalesce(func.sum(Contribution.points), 0))
        .filter(Contribution.user_id == user.id)
        .scalar()
        or 0
    )
    quality = (
        db.session.query(func.coalesce(func.sum(Contribution.quality_points), 0))
        .filter(Contribution.user_id == user.id)
        .scalar()
        or 0
    )

    return {
        "submissions": total_submissions,
        "approved": approved,
        "context_submissions": context_submissions,
        "languages": languages,
        "reviews": reviews,
        "support_received": support_received,
        "votes_cast": votes_cast,
        "activity_points": int(activity),
        "quality_points": int(quality),
        "reputation": int(quality) * 2 + int(activity),
    }


def tier_for_reputation(reputation):
    tier = TIERS[0][0]
    for code, _label, minimum in TIERS:
        if reputation >= minimum:
            tier = code
    return tier


def rank_for_user(user, metrics=None):
    metrics = metrics or metrics_for_user(user)
    rep = metrics["reputation"]
    return {
        "tier": tier_for_reputation(rep),
        "tier_label": TIER_LABELS[tier_for_reputation(rep)],
        "reputation": rep,
        "metrics": metrics,
    }


def leaderboard(limit=50, min_submissions=1):
    rows = []
    users = User.query.filter_by(is_active=True).filter(User.is_seed.is_(False)).all()
    for user in users:
        metrics = metrics_for_user(user)
        if metrics["submissions"] < min_submissions and metrics["reviews"] < 1:
            continue
        rows.append(
            {
                "user": user,
                "reputation": metrics["reputation"],
                "tier_label": TIER_LABELS[tier_for_reputation(metrics["reputation"])],
                "approved": metrics["approved"],
                "submissions": metrics["submissions"],
                "reviews": metrics["reviews"],
            }
        )
    rows.sort(key=lambda r: (r["reputation"], r["approved"]), reverse=True)
    return rows[:limit]


# --------------------------------------------------------------------------- #
# Milestones
# --------------------------------------------------------------------------- #

def evaluate_milestones(user):
    """Award any newly-earned milestones. Returns the list of new awards."""
    if user is None or user.is_seed:
        return []
    metrics = metrics_for_user(user)
    earned_ids = {a.milestone_id for a in UserMilestone.query.filter_by(user_id=user.id)}
    new_awards = []
    milestones = Milestone.query.order_by(Milestone.sort_order).all()
    for milestone in milestones:
        if milestone.id in earned_ids:
            continue
        value = metrics.get(milestone.metric, 0)
        if value >= milestone.threshold:
            award = UserMilestone(user_id=user.id, milestone_id=milestone.id)
            db.session.add(award)
            db.session.flush()
            record_contribution(
                user, "milestone", ref_type="milestone", ref_id=milestone.id,
                points=milestone.points, quality_points=0,
            )
            earned_ids.add(milestone.id)
            new_awards.append(milestone)
    return new_awards


def milestones_status(user):
    """Return all milestones with whether the user earned them."""
    earned = {
        a.milestone_id: a
        for a in UserMilestone.query.filter_by(user_id=user.id).all()
    }
    out = []
    for milestone in Milestone.query.order_by(Milestone.sort_order).all():
        out.append(
            {
                "milestone": milestone,
                "earned": milestone.id in earned,
                "achieved_at": earned[milestone.id].achieved_at
                if milestone.id in earned else None,
            }
        )
    return out


def recompute_submission_quality(submission):
    """Simple, transparent quality score based on community agreement."""
    votes = submission.votes
    if not votes:
        submission.quality_score = 0.0
    else:
        submission.quality_score = round(submission.agreement_ratio * len(votes), 2)
    return submission.quality_score
