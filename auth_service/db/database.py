from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auth_service.models.models import Base # Import Base from your models file

# DATABASE_URL for PostgreSQL.
# TODO: This should be configured via environment variables in a production setup.
DATABASE_URL = "postgresql://user:password@localhost:5432/auth_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    # This is for initial setup, you might want to handle this differently
    # e.g., using Alembic for migrations in a real application.
    print("Creating database and tables...")
    create_db_and_tables()
    print("Database and tables created (if they didn't exist).")
