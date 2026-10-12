"""Database models for the Kenyan cybersecurity translation platform.

The schema is intentionally explicit and auditable:

* Reference data: counties, languages, dialects, terms.
* Contributors: users and their contributions, votes and reviews.
* Output: canonical (approved) translations plus a full revision history.
* Recognition: milestones and an append-only contributions ledger.
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

ROLE_CONTRIBUTOR = "contributor"
ROLE_REVIEWER = "reviewer"
ROLE_ADMIN = "admin"
ROLE_LABELS = {
    ROLE_CONTRIBUTOR: "Contributor",
    ROLE_REVIEWER: "Reviewer",
    ROLE_ADMIN: "Administrator",
}

CATEGORY_GLOSSARY = "glossary"
CATEGORY_MESSAGE = "message"
CATEGORY_LABELS = {
    CATEGORY_GLOSSARY: "Glossary term",
    CATEGORY_MESSAGE: "Awareness message",
}

# Submission lifecycle
STATUS_CANDIDATE = "candidate"
STATUS_SHORTLISTED = "shortlisted"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_LABELS = {
    STATUS_CANDIDATE: "Candidate",
    STATUS_SHORTLISTED: "Shortlisted",
    STATUS_NEEDS_REVIEW: "Needs review",
    STATUS_APPROVED: "Approved",
    STATUS_REJECTED: "Rejected",
}

# Canonical entry lifecycle
CANON_APPROVED = "approved"
CANON_DISPUTED = "disputed"
CANON_NEEDS_REVIEW = "needs_review"
CANON_REPLACED = "replaced"
CANON_STATUS_LABELS = {
    CANON_APPROVED: "Approved / canonical",
    CANON_DISPUTED: "Disputed",
    CANON_NEEDS_REVIEW: "Needs further review",
    CANON_REPLACED: "Replaced",
}

VOTE_SUPPORT = "support"
VOTE_OPPOSE = "oppose"
VOTE_LABELS = {VOTE_SUPPORT: "Supports", VOTE_OPPOSE: "Disputes"}

# Review actions
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_REQUEST_REVISION = "request_revision"
ACTION_FLAG = "flag"
ACTION_REPLACE = "replace"
ACTION_COMMENT = "comment"
ACTION_LABELS = {
    ACTION_APPROVE: "Approved",
    ACTION_REJECT: "Rejected",
    ACTION_REQUEST_REVISION: "Requested revision",
    ACTION_FLAG: "Flagged as misleading",
    ACTION_REPLACE: "Replaced canonical",
    ACTION_COMMENT: "Commented",
}


# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #

class County(db.Model):
    __tablename__ = "counties"

    id = db.Column(Integer, primary_key=True)
    code = db.Column(String(8), unique=True, nullable=False)
    name = db.Column(String(80), unique=True, nullable=False)
    region = db.Column(String(80), nullable=True)

    languages = relationship(
        "Language", secondary="language_counties", back_populates="counties"
    )

    def __repr__(self):
        return f"<County {self.name}>"


class Language(db.Model):
    __tablename__ = "languages"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(80), unique=True, nullable=False)
    native_name = db.Column(String(120), nullable=True)
    iso_code = db.Column(String(16), nullable=True)
    is_active = db.Column(Boolean, default=True, nullable=False)

    dialects = relationship(
        "Dialect", back_populates="language", cascade="all, delete-orphan",
        order_by="Dialect.name",
    )
    counties = relationship(
        "County", secondary="language_counties", back_populates="languages"
    )

    def __repr__(self):
        return f"<Language {self.name}>"


class Dialect(db.Model):
    __tablename__ = "dialects"
    __table_args__ = (UniqueConstraint("language_id", "name", name="uq_dialect_lang"),)

    id = db.Column(Integer, primary_key=True)
    language_id = db.Column(Integer, ForeignKey("languages.id"), nullable=False)
    name = db.Column(String(80), nullable=False)
    is_active = db.Column(Boolean, default=True, nullable=False)

    language = relationship("Language", back_populates="dialects")

    def __repr__(self):
        return f"<Dialect {self.name} ({self.language_id})>"


class LanguageCounty(db.Model):
    __tablename__ = "language_counties"

    language_id = db.Column(
        Integer, ForeignKey("languages.id"), primary_key=True
    )
    county_id = db.Column(Integer, ForeignKey("counties.id"), primary_key=True)


class Term(db.Model):
    __tablename__ = "terms"

    id = db.Column(Integer, primary_key=True)
    slug = db.Column(String(100), unique=True, nullable=False)
    category = db.Column(String(20), nullable=False, default=CATEGORY_GLOSSARY)
    sort_order = db.Column(Integer, default=0, nullable=False)
    english_name = db.Column(String(200), nullable=False)
    english_definition = db.Column(Text, nullable=False)
    swahili_name = db.Column(String(200), nullable=True)
    swahili_definition = db.Column(Text, nullable=True)
    source_column = db.Column(String(200), nullable=True)
    is_active = db.Column(Boolean, default=True, nullable=False)

    submissions = relationship(
        "Submission", back_populates="term", cascade="all, delete-orphan"
    )
    canonicals = relationship(
        "CanonicalTranslation", back_populates="term", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Term {self.slug}>"


# --------------------------------------------------------------------------- #
# Contributors
# --------------------------------------------------------------------------- #

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    email = db.Column(String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(String(120), nullable=False)
    password_hash = db.Column(String(255), nullable=True)
    role = db.Column(String(20), default=ROLE_CONTRIBUTOR, nullable=False)

    county_id = db.Column(Integer, ForeignKey("counties.id"), nullable=True)
    preferred_language_id = db.Column(Integer, ForeignKey("languages.id"), nullable=True)
    preferred_dialect_id = db.Column(Integer, ForeignKey("dialects.id"), nullable=True)

    is_active = db.Column(Boolean, default=True, nullable=False)
    is_seed = db.Column(Boolean, default=False, nullable=False)
    created_at = db.Column(DateTime, default=utcnow, nullable=False)
    last_login_at = db.Column(DateTime, nullable=True)

    county = relationship("County")
    preferred_language = relationship("Language", foreign_keys=[preferred_language_id])
    preferred_dialect = relationship("Dialect", foreign_keys=[preferred_dialect_id])

    submissions = relationship("Submission", back_populates="user")
    votes = relationship("Vote", back_populates="user")

    # -- helpers ----------------------------------------------------------- #
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_reviewer(self):
        return self.role in (ROLE_REVIEWER, ROLE_ADMIN)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def initials(self):
        parts = [p for p in (self.display_name or "").split() if p]
        if not parts:
            return (self.email or "?")[0].upper()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Submission(db.Model):
    """A contributor-proposed translation (or definition/example) for a term."""

    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submission_term_lang", "term_id", "language_id", "dialect_id"),
    )

    id = db.Column(Integer, primary_key=True)
    term_id = db.Column(Integer, ForeignKey("terms.id"), nullable=False)
    language_id = db.Column(Integer, ForeignKey("languages.id"), nullable=False)
    dialect_id = db.Column(Integer, ForeignKey("dialects.id"), nullable=True)
    user_id = db.Column(Integer, ForeignKey("users.id"), nullable=False)

    text = db.Column(Text, nullable=False)
    usage_note = db.Column(Text, nullable=True)   # how it is used / understood
    example = db.Column(Text, nullable=True)      # natural example sentence

    status = db.Column(String(20), default=STATUS_CANDIDATE, nullable=False)
    quality_score = db.Column(Float, default=0.0, nullable=False)

    is_seed = db.Column(Boolean, default=False, nullable=False)
    consent_public = db.Column(Boolean, default=False, nullable=False)

    created_at = db.Column(DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    term = relationship("Term", back_populates="submissions")
    language = relationship("Language")
    dialect = relationship("Dialect")
    user = relationship("User", back_populates="submissions")
    votes = relationship(
        "Vote", back_populates="submission", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="submission", cascade="all, delete-orphan"
    )

    # -- scoring ----------------------------------------------------------- #
    @property
    def support_count(self):
        return sum(1 for v in self.votes if v.value == VOTE_SUPPORT)

    @property
    def oppose_count(self):
        return sum(1 for v in self.votes if v.value == VOTE_OPPOSE)

    @property
    def vote_count(self):
        return len(self.votes)

    @property
    def agreement_ratio(self):
        if not self.votes:
            return 0.0
        return self.support_count / len(self.votes)

    def __repr__(self):
        return f"<Submission {self.id} term={self.term_id} lang={self.language_id}>"


class Vote(db.Model):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("submission_id", "user_id", name="uq_vote_submission_user"),
    )

    id = db.Column(Integer, primary_key=True)
    submission_id = db.Column(Integer, ForeignKey("submissions.id"), nullable=False)
    user_id = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    value = db.Column(String(10), nullable=False, default=VOTE_SUPPORT)
    weight = db.Column(Float, default=1.0, nullable=False)
    created_at = db.Column(DateTime, default=utcnow, nullable=False)

    submission = relationship("Submission", back_populates="votes")
    user = relationship("User", back_populates="votes")


class Review(db.Model):
    """Immutable audit record of every review decision."""

    __tablename__ = "reviews"

    id = db.Column(Integer, primary_key=True)
    submission_id = db.Column(Integer, ForeignKey("submissions.id"), nullable=False)
    reviewer_id = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    action = db.Column(String(30), nullable=False)
    note = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, default=utcnow, nullable=False)

    submission = relationship("Submission", back_populates="reviews")
    reviewer = relationship("User")


class CanonicalTranslation(db.Model):
    """The approved/recommended translation for a (term, language, dialect)."""

    __tablename__ = "canonical_translations"
    __table_args__ = (
        UniqueConstraint(
            "term_id", "language_id", "dialect_id", name="uq_canonical_scope"
        ),
    )

    id = db.Column(Integer, primary_key=True)
    term_id = db.Column(Integer, ForeignKey("terms.id"), nullable=False)
    language_id = db.Column(Integer, ForeignKey("languages.id"), nullable=False)
    dialect_id = db.Column(Integer, ForeignKey("dialects.id"), nullable=True)

    submission_id = db.Column(Integer, ForeignKey("submissions.id"), nullable=True)
    text = db.Column(Text, nullable=False)
    definition = db.Column(Text, nullable=True)
    context = db.Column(Text, nullable=True)
    status = db.Column(String(20), default=CANON_APPROVED, nullable=False)
    revision_no = db.Column(Integer, default=1, nullable=False)

    approved_by = db.Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(DateTime, nullable=True)
    created_at = db.Column(DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    term = relationship("Term", back_populates="canonicals")
    language = relationship("Language")
    dialect = relationship("Dialect")
    submission = relationship("Submission")
    approver = relationship("User")
    revisions = relationship(
        "CanonicalRevision", back_populates="canonical", cascade="all, delete-orphan",
        order_by="desc(CanonicalRevision.revision_no)",
    )


class CanonicalRevision(db.Model):
    """Snapshot history so every approval/replacement is auditable."""

    __tablename__ = "canonical_revisions"

    id = db.Column(Integer, primary_key=True)
    canonical_id = db.Column(
        Integer, ForeignKey("canonical_translations.id"), nullable=False
    )
    revision_no = db.Column(Integer, nullable=False)
    change_type = db.Column(String(20), nullable=False, default="create")
    snapshot = db.Column(Text, nullable=False)  # JSON payload
    note = db.Column(Text, nullable=True)
    changed_by = db.Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = db.Column(DateTime, default=utcnow, nullable=False)

    canonical = relationship("CanonicalTranslation", back_populates="revisions")
    changer = relationship("User")


# --------------------------------------------------------------------------- #
# Recognition
# --------------------------------------------------------------------------- #

class Milestone(db.Model):
    __tablename__ = "milestones"

    id = db.Column(Integer, primary_key=True)
    code = db.Column(String(50), unique=True, nullable=False)
    name = db.Column(String(120), nullable=False)
    description = db.Column(Text, nullable=True)
    metric = db.Column(String(40), nullable=False)
    threshold = db.Column(Integer, default=1, nullable=False)
    points = db.Column(Integer, default=0, nullable=False)
    sort_order = db.Column(Integer, default=0, nullable=False)

    awards = relationship("UserMilestone", back_populates="milestone")

    def __repr__(self):
        return f"<Milestone {self.code}>"


class UserMilestone(db.Model):
    __tablename__ = "user_milestones"
    __table_args__ = (
        UniqueConstraint("user_id", "milestone_id", name="uq_user_milestone"),
    )

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    milestone_id = db.Column(Integer, ForeignKey("milestones.id"), nullable=False)
    achieved_at = db.Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User")
    milestone = relationship("Milestone", back_populates="awards")


class Contribution(db.Model):
    """Append-only ledger of contributor activity, used for ranking."""

    __tablename__ = "contributions"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(String(40), nullable=False)
    ref_type = db.Column(String(30), nullable=True)
    ref_id = db.Column(Integer, nullable=True)
    points = db.Column(Integer, default=0, nullable=False)
    quality_points = db.Column(Integer, default=0, nullable=False)
    created_at = db.Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User")

    def __repr__(self):
        return f"<Contribution {self.action} user={self.user_id} +{self.points}>"
