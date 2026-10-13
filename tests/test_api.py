from app.extensions import db
from app.models import Submission
from app.services import consensus


def test_health_and_reference_endpoints(client):
    assert client.get("/api/v1/health").get_json()["status"] == "ok"
    assert client.get("/api/v1/counties").get_json()["count"] == 47
    assert client.get("/api/v1/languages").get_json()["count"] >= 20
    assert client.get("/api/v1/terms").get_json()["count"] == 35


def test_stats_endpoint_for_learners(client):
    data = client.get("/api/v1/stats").get_json()
    assert "totals" in data and "languages" in data and "top_contributors" in data
    totals = data["totals"]
    assert totals["terms"] == 35
    assert totals["counties"] == 47
    assert totals["languages"] >= 20
    # every language carries the fields the learners UI reads
    for lang in data["languages"]:
        for key in ["name", "native_name", "submissions", "approved",
                    "contributors", "dialect_count", "dialects"]:
            assert key in lang
        assert isinstance(lang["dialects"], list)


def test_translations_empty_until_approved(client):
    assert client.get("/api/v1/translations").get_json()["count"] == 0


def test_approved_translation_is_served(client, app, admin_user, contributor,
                                        sample_term, sample_language):
    sub = consensus.create_submission(
        contributor, sample_term, sample_language, None, "served phrase"
    )
    db.session.commit()
    consensus.approve_canonical(sample_term, sample_language, None, sub, admin_user)
    db.session.commit()

    data = client.get("/api/v1/translations").get_json()
    assert data["count"] == 1
    record = data["translations"][0]
    assert record["term"] == "phishing"
    assert record["language"] == "Kikuyu"
    assert record["translation"] == "served phrase"

    by_term = client.get("/api/v1/translations/phishing").get_json()
    assert by_term["count"] == 1

    unknown = client.get("/api/v1/translations?language=Klingon")
    assert unknown.status_code == 404


def test_public_downloads(client, app, admin_user, contributor,
                          sample_term, sample_language):
    sub = consensus.create_submission(
        contributor, sample_term, sample_language, None, "download phrase"
    )
    db.session.commit()
    consensus.approve_canonical(sample_term, sample_language, None, sub, admin_user)
    db.session.commit()

    json_resp = client.get("/downloads/translations.json")
    assert json_resp.status_code == 200
    assert b"download phrase" in json_resp.data

    csv_resp = client.get("/downloads/translations.csv")
    assert csv_resp.status_code == 200
    assert b"download phrase" in csv_resp.data


def test_submissions_not_leaked_in_public_export(client, app, contributor,
                                                 sample_term, sample_language):
    consensus.create_submission(
        contributor, sample_term, sample_language, None, "unapproved secret"
    )
    db.session.commit()
    resp = client.get("/downloads/translations.json")
    assert b"unapproved secret" not in resp.data
