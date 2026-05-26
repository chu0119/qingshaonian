from sqlalchemy.orm import Session

from ..config import settings
from ..models.user import School
from ..questionnaire_bank import ensure_builtin_questionnaires
from .demo_seed_service import seed_demo_school_data


DEMO_ENVS = {"demo", "development"}


def initialize_seed_data(db: Session, current_settings=settings) -> dict:
    env = (getattr(current_settings, "APP_ENV", "demo") or "demo").lower()
    result = {"builtin_initialized": False, "demo_seeded_schools": []}

    if getattr(current_settings, "INIT_BUILTIN_QUESTIONNAIRES", False):
        ensure_builtin_questionnaires(db)
        result["builtin_initialized"] = True

    if env in DEMO_ENVS and getattr(current_settings, "INIT_DEMO_DATA", False):
        result["demo_seeded_schools"] = seed_demo_data(db, current_settings=current_settings)

    return result


def seed_demo_data(db: Session, school_id: int | None = None, current_settings=settings) -> list[int]:
    env = (getattr(current_settings, "APP_ENV", "demo") or "demo").lower()
    if env not in DEMO_ENVS:
        return []

    target_query = db.query(School)
    if school_id is not None:
        target_query = target_query.filter(School.id == school_id)

    seeded_school_ids: list[int] = []
    for school in target_query.order_by(School.id).all():
        if seed_demo_school_data(db, school.id):
            seeded_school_ids.append(school.id)
    return seeded_school_ids
