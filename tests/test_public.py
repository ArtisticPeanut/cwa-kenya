def test_public_pages(client):
    for path in ["/", "/languages", "/tasks", "/tasks/phishing", "/browse",
                 "/leaderboard", "/about", "/downloads", "/terms/phishing",
                 "/learn", "/auth/login", "/auth/register"]:
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_unknown_term_returns_404(client):
    assert client.get("/tasks/does-not-exist").status_code == 404


def test_select_language_sets_session(client):
    from app.models import Language

    lang = Language.query.filter_by(name="Dholuo").first()
    resp = client.get(f"/languages/set/{lang.id}", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dholuo" in resp.data


def test_learn_quiz_builds_question_from_consented_samples(app, client, contributor):
    from app.extensions import db
    from app.models import Language, STATUS_CANDIDATE, Submission, Term

    lang = Language.query.filter_by(name="Kikuyu").first()
    terms = Term.query.limit(4).all()
    for i, term in enumerate(terms):
        db.session.add(Submission(
            term_id=term.id, language_id=lang.id, user_id=contributor.id,
            text=f"kikuyu-word-{i}", status=STATUS_CANDIDATE, consent_public=True,
        ))
    db.session.commit()

    data = client.get("/learn/quiz?language=Kikuyu").get_json()
    assert data["available"] is True
    q = data["question"]
    assert q["term"] in [t.english_name for t in terms]
    assert len(q["options"]) == 4
    assert q["options"][q["answer_index"]]  # answer points at a real option

    # a language with no consented samples falls back gracefully
    empty = client.get("/learn/quiz?language=Somali").get_json()
    assert empty["available"] is False


def test_learn_quiz_unknown_language(client):
    assert client.get("/learn/quiz?language=Klingon").status_code == 404


def test_learn_word_serves_consented_sample(app, client, contributor):
    from app.extensions import db
    from app.models import (
        CATEGORY_MESSAGE,
        Language,
        STATUS_CANDIDATE,
        Submission,
        Term,
    )

    lang = Language.query.filter_by(name="Kikuyu").first()
    glossary_term = Term.query.filter_by(category="glossary", slug="phishing").first()
    db.session.add(Submission(
        term_id=glossary_term.id, language_id=lang.id, user_id=contributor.id,
        text="test-kikuyu-phishing", status=STATUS_CANDIDATE, consent_public=True,
    ))
    db.session.commit()

    data = client.get("/learn/word?language=Kikuyu&category=glossary").get_json()
    assert data["available"] is True
    assert data["word"]["translation"] == "test-kikuyu-phishing"
    assert data["word"]["verified"] is False
    assert data["word"]["category"] == "glossary"

    # no message samples in this language yet -> graceful "not enough words"
    messages = client.get("/learn/word?language=Kikuyu&category=" + CATEGORY_MESSAGE)
    assert messages.get_json()["available"] is False

    assert client.get("/learn/word?language=Klingon").status_code == 404
