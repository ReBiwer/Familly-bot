from abc import ABC

from src.application.repositories.base import ISQLRepository
from src.domain.entities.resume import JobExperienceEntity, ResumeEntity


class IResumeRepository[ET: ResumeEntity](ISQLRepository[ResumeEntity], ABC): ...


class IJobExperienceRepository[ET: JobExperienceEntity](
    ISQLRepository[JobExperienceEntity], ABC
): ...
