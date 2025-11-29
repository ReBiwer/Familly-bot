import datetime

import pytest
from src.domain.entities.resume import JobExperienceEntity, ResumeEntity
from src.domain.entities.user import UserEntity


@pytest.fixture(scope="package")
def test_job_experience_entity() -> JobExperienceEntity:
    return JobExperienceEntity(
        company="ННК-Северная нефть",
        position="Ведущий инженер",
        start=datetime.datetime(year=2024, month=7, day=1),
        end=None,
        description="Катать вату",
    )


@pytest.fixture(scope="package")
def test_resume_entity(test_job_experience_entity: JobExperienceEntity) -> ResumeEntity:
    return ResumeEntity(
        hh_id="asjhfjha78",
        title="Python разработчик",
        name="Владимир",
        surname="Быков",
        job_experience=[test_job_experience_entity],
        skills={"python", "FastAPI", "pydantic", "pytest"},
        contact_phone="89091260929",
        contact_email="vovka1998@gmail.com",  # type: ignore
    )


@pytest.fixture(scope="package")
def test_user_entity(test_resume_entity: ResumeEntity) -> UserEntity:
    return UserEntity(
        hh_id="12351ad213",
        name="Владимир",
        mid_name="Николаевич",
        last_name="Быков",
        phone="89091260929",
        email="vovka1998@gmail.com",  # type: ignore
        resumes=[test_resume_entity],
    )
