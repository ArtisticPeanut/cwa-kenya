from app.models import County, Dialect, Language, Milestone, Term


def test_reference_data_seeded(app):
    assert County.query.count() == 47
    assert Language.query.filter_by(name="Kikuyu").first() is not None
    assert Dialect.query.count() >= 70
    assert Term.query.count() == 35
    assert Term.query.filter_by(category="glossary").count() == 30
    assert Term.query.filter_by(category="message").count() == 5
    assert Milestone.query.count() == 9


def test_county_language_suggestions(app):
    meru = County.query.filter_by(name="Meru").first()
    assert meru is not None
    assert any(lang.name == "Kimeru" for lang in meru.languages)
