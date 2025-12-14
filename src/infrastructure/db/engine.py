from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.infrastructure.settings.app import app_settings

engine = create_async_engine(app_settings.DB.db_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
