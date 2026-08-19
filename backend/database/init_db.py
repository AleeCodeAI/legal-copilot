
from database.base import Base
from database.session import engine

# Import all models so SQLAlchemy knows them
from database.models.execution_table import ExecutionTable
from database.models.retrieval_table import RetrievalTable
from database.models.synthesis_table import SynthesisTable

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()