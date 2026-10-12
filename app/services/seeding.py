"""Idempotent seeding of reference data."""

from app.extensions import db
from app.models import (
    CATEGORY_GLOSSARY,
    CATEGORY_MESSAGE,
    County,
    Dialect,
    Language,
    Milestone,
    Term,
)
from app.services import seed_data


def seed_all(verbose=False):
    stats = {
        "counties": seed_counties(verbose),
        "languages": seed_languages(verbose),
        "terms": seed_terms(verbose),
        "milestones": seed_milestones(verbose),
    }
    db.session.commit()
    return stats


def seed_counties(verbose=False):
    created = 0
    existing = {c.code: c for c in County.query.all()}
    for code, name, region in seed_data.COUNTIES:
        if code not in existing:
            c = County(code=code, name=name, region=region)
            db.session.add(c)
            existing[code] = c
            created += 1
    db.session.flush()
    if verbose:
        print(f"  counties: +{created}")
    return created


def seed_languages(verbose=False):
    county_by_name = {c.name: c for c in County.query.all()}
    lang_created = 0
    dialect_created = 0
    for name, native, iso, dialects, county_names in seed_data.LANGUAGES:
        lang = Language.query.filter_by(name=name).first()
        if not lang:
            lang = Language(name=name, native_name=native, iso_code=iso)
            db.session.add(lang)
            db.session.flush()
            lang_created += 1

        existing_dialects = {d.name for d in lang.dialects}
        for dname in dialects:
            if dname not in existing_dialects:
                db.session.add(Dialect(language_id=lang.id, name=dname))
                dialect_created += 1

        existing_counties = {c.id for c in lang.counties}
        for cname in county_names:
            county = county_by_name.get(cname)
            if county and county.id not in existing_counties:
                lang.counties.append(county)
                existing_counties.add(county.id)

    db.session.flush()
    if verbose:
        print(f"  languages: +{lang_created}, dialects: +{dialect_created}")
    return {"languages": lang_created, "dialects": dialect_created}


def seed_terms(verbose=False):
    created = 0
    order = 0
    for row in seed_data.GLOSSARY:
        order += 1
        created += _upsert_term(*row, category=CATEGORY_GLOSSARY, sort_order=order)
    for row in seed_data.MESSAGES:
        order += 1
        created += _upsert_term(*row, category=CATEGORY_MESSAGE, sort_order=order)
    db.session.flush()
    if verbose:
        print(f"  terms: +{created}")
    return created


def _upsert_term(slug, english_name, english_def, sw_name, sw_def, source_column,
                 category, sort_order):
    term = Term.query.filter_by(slug=slug).first()
    if term:
        return 0
    db.session.add(
        Term(
            slug=slug,
            category=category,
            sort_order=sort_order,
            english_name=english_name,
            english_definition=english_def,
            swahili_name=sw_name,
            swahili_definition=sw_def,
            source_column=source_column,
        )
    )
    return 1


def seed_milestones(verbose=False):
    created = 0
    for code, name, desc, metric, threshold, points, order in seed_data.MILESTONES:
        if not Milestone.query.filter_by(code=code).first():
            db.session.add(
                Milestone(
                    code=code, name=name, description=desc, metric=metric,
                    threshold=threshold, points=points, sort_order=order,
                )
            )
            created += 1
    db.session.flush()
    if verbose:
        print(f"  milestones: +{created}")
    return created
