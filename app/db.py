import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./cerberus.db')
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Create new tables and apply additive changes for existing deployments."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    columns = {column['name'] for column in inspector.get_columns('border_events')}
    if 'passport_verification_id' not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                'ALTER TABLE border_events ADD COLUMN passport_verification_id INTEGER '
                'REFERENCES passport_verifications(id)'
            ))
    with engine.begin() as connection:
        connection.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_border_events_passport_verification_id '
            'ON border_events (passport_verification_id)'
        ))
