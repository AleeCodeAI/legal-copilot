from sqlalchemy import Column, Integer, UUID, Text, ForeignKey

from database.base import Base


class SynthesisTable(Base):
    __tablename__ = "synthesis_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(
        UUID,
        ForeignKey("execution_table.execution_id"),
        nullable=False,
    )
    answer = Column(Text, nullable=True)
    reasoning_summary = Column(Text, nullable=False)