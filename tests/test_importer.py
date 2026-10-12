"""Classification integrity: mislabelled dialects must not leak across languages."""


def test_repair_reclassifies_mislabeled_dialect(app, contributor):
    from app.extensions import db
    from app.models import (
        Dialect,
        Language,
        STATUS_CANDIDATE,
        Submission,
        Term,
    )
    from app.services import importer

    ks = Language.query.filter_by(name="Kiswahili").first()
    ek = Language.query.filter_by(name="Ekegusii").first()
    term = Term.query.first()

    # Simulate the real bug: a "Kisii" dialect (and its Ekegusii sample) filed
    # under Kiswahili because the respondent picked Swahili as their language.
    wrong = Dialect(language_id=ks.id, name="Kisii")
    db.session.add(wrong)
    db.session.flush()
    sub = Submission(
        term_id=term.id, language_id=ks.id, dialect_id=wrong.id,
        user_id=contributor.id, text="ekero", status=STATUS_CANDIDATE,
        consent_public=True,
    )
    db.session.add(sub)
    db.session.commit()

    result = importer.repair_misclassified(verbose=False)

    assert result["moved"] == 1
    db.session.refresh(sub)
    assert sub.language_id == ek.id
    assert sub.dialect.language_id == ek.id


def test_translation_pool_excludes_cross_language_dialects(app, contributor):
    from app.extensions import db
    from app.main import _translation_pool
    from app.models import (
        Dialect,
        Language,
        STATUS_CANDIDATE,
        Submission,
        Term,
    )

    ks = Language.query.filter_by(name="Kiswahili").first()
    terms = Term.query.limit(2).all()

    def get_or_make(name):
        d = Dialect.query.filter_by(language_id=ks.id, name=name).first()
        if d is None:
            d = Dialect(language_id=ks.id, name=name)
            db.session.add(d)
        return d

    sheng = get_or_make("Sheng")
    kamba = get_or_make("Kamba")  # belongs to Kikamba
    db.session.flush()

    db.session.add(Submission(
        term_id=terms[0].id, language_id=ks.id, dialect_id=kamba.id,
        user_id=contributor.id, text="kikamba-text", status=STATUS_CANDIDATE,
        consent_public=True,
    ))
    db.session.add(Submission(
        term_id=terms[1].id, language_id=ks.id, dialect_id=sheng.id,
        user_id=contributor.id, text="kiswahili-text", status=STATUS_CANDIDATE,
        consent_public=True,
    ))
    db.session.commit()

    pool = _translation_pool(ks.id)

    assert terms[0].id not in pool           # Kamba sample rejected
    assert pool[terms[1].id]["text"] == "kiswahili-text"
