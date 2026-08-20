from sqlalchemy import Column, String, UUID, JSON, Text
from database.base import Base


class HistoryTable(Base):
    __tablename__ = "history_table"

    # Same ID used as the Langfuse session_id
    history_id = Column(UUID, primary_key=True, nullable=False)

    query = Column(String, nullable=False)
    answer = Column(Text, nullable=True)
    citations = Column(JSON, nullable=True)
