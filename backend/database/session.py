from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from configs.settings import get_settings

settings = get_settings()

engine = create_engine(settings.database.service_url, echo=False)
SessionLocal = sessionmaker(bind=engine)