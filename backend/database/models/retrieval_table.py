from sqlalchemy import (
    Column,
    Integer,
    Float,
    Boolean,
    UUID,
    Text,
    ForeignKey,
    JSON,
    String
)

from database.base import Base


class RetrievalTable(Base):
    __tablename__ = "retrieval_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(
        UUID,
        ForeignKey("execution_table.execution_id"),
        nullable=False,
    )

    pass_number = Column(String, nullable=False)
    sufficient = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    refined_query = Column(Text, nullable=True)
    selected_chunks = Column(JSON, nullable=True)