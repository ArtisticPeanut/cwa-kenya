from app.extensions import db
from app.models import (
    ACTION_APPROVE,
    CANON_APPROVED,
    CanonicalRevision,
    CanonicalTranslation,
    Submission,
    User,
    VOTE_SUPPORT,
)
from app.services import consensus, recognition
from tests.conftest import make_user


def test_register_and_login(client, app):
    resp = client.post(
        "/auth/register",
        data={
            "display_name": "Amina Wanjiru",
            "email": "amina@test.ke",
            "password": "supersecret1",
            "confirm": "supersecret1",
            "county_id": "0",
            "preferred_language_id": "0",
            "preferred_dialect_id": "0",
            "consent": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert User.query.filter_by(email="amina@test.ke").first() is not None


def test_submission_requires_meaningful_text(client, app, contributor,
                                             sample_term, sample_language):
    client.post("/auth/login", data={"email": contributor.email,
                                     "password": "supersecret1"})
    client.post(
        f"/tasks/{sample_term.slug}/submit",
        data={"language_id": sample_language.id, "dialect_id": "0", "text": "  "},
    )
    assert Submission.query.count() == 0


def test_submission_and_vote_flow(app, contributor, sample_term, sample_language):
    sub = consensus.create_submission(
        contributor, sample_term, sample_language, None,
        "Njuguna ya udanganyifu", usage_note="common phrase", example="Example",
    )
    db.session.commit()
    assert sub.status == "candidate"

    voter = make_user(app, "voter@test.ke", "Voter")
    consensus.cast_vote(voter, sub, VOTE_SUPPORT)
    db.session.commit()
    assert sub.support_count == 1
    assert sub.agreement_ratio == 1.0


def test_self_vote_rejected(app, contributor, sample_term, sample_language):
    sub = consensus.create_submission(
        contributor, sample_term, sample_language, None, "Some translation"
    )
    db.session.commit()
    try:
        consensus.cast_vote(contributor, sub, VOTE_SUPPORT)
        raised = False
    except ValueError as exc:
        raised = True
        assert "own" in str(exc)
    assert raised


def test_consensus_reached_then_canonical_approval(app, admin_user, contributor,
                                                   sample_term, sample_language):
    sub = consensus.create_submission(
        contributor, sample_term, sample_language, None, "Verified phrase",
        usage_note="definition", example="example",
    )
    db.session.commit()
    for i in range(3):
        voter = make_user(app, f"v{i}@test.ke", f"Voter {i}")
        consensus.cast_vote(voter, sub, VOTE_SUPPORT)
    db.session.commit()

    scope = consensus.scope_consensus(sample_term.id, sample_language.id, None)
    assert scope["state"] == consensus.CONSENSUS_REACHED

    canon = consensus.approve_canonical(
        sample_term, sample_language, None, sub, admin_user, note="ok"
    )
    db.session.commit()

    assert canon.status == CANON_APPROVED
    assert canon.revision_no == 1
    assert canon.text == "Verified phrase"
    assert sub.status == "approved"
    assert CanonicalRevision.query.filter_by(canonical_id=canon.id).count() == 1

    # Approving a different candidate replaces it and preserves history.
    other = consensus.create_submission(
        contributor, sample_term, sample_language, None, "Alternative phrase"
    )
    db.session.commit()
    canon2 = consensus.approve_canonical(
        sample_term, sample_language, None, other, admin_user, note="replace"
    )
    db.session.commit()
    assert canon2.id == canon.id
    assert canon2.revision_no == 2
    assert canon2.text == "Alternative phrase"
    assert CanonicalRevision.query.filter_by(canonical_id=canon.id).count() == 2


def test_milestones_and_reputation(app, contributor, sample_term, sample_language):
    consensus.create_submission(contributor, sample_term, sample_language, None,
                                "one", usage_note="ctx", example="ex")
    db.session.commit()
    metrics = recognition.metrics_for_user(contributor)
    assert metrics["submissions"] == 1
    assert metrics["context_submissions"] == 1
    assert metrics["activity_points"] > 0
    rank = recognition.rank_for_user(contributor)
    assert rank["tier"] in recognition.TIER_LABELS


def test_ambiguous_consensus_preserved(app, contributor, sample_term, sample_language):
    a = consensus.create_submission(contributor, sample_term, sample_language, None, "A")
    b = consensus.create_submission(contributor, sample_term, sample_language, None, "B")
    db.session.commit()
    for i in range(4):
        v = make_user(app, f"a{i}@test.ke", f"A{i}")
        consensus.cast_vote(v, a, VOTE_SUPPORT)
    for i in range(4):
        v = make_user(app, f"b{i}@test.ke", f"B{i}")
        consensus.cast_vote(v, b, VOTE_SUPPORT)
    db.session.commit()
    scope = consensus.scope_consensus(sample_term.id, sample_language.id, None)
    assert scope["state"] == consensus.CONSENSUS_AMBIGUOUS
    assert scope["leader"] is None
