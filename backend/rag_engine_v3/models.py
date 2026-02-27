import uuid
from sqlalchemy.orm import Mapped

from ..database.model import Base

class QdrantIds(Base):
    """ORM-модель точек векторной бд.

    Attributes:
        ids(uuid): ID точки в векторной бд
        table_name(str): Название таблицы, соответствующей точке
    """
    ids: Mapped[uuid.UUID]
    table_name: Mapped[str]