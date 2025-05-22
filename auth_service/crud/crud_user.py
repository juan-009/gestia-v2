from sqlalchemy.orm import Session
from ..models.models import User
from ..schemas.user import UserCreate
from ..core.security import hash_password

def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Retrieves a user from the database by their email address.
    """
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> User | None:
    """
    Retrieves a user from the database by their username.
    """
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate) -> User:
    """
    Creates a new user in the database.
    """
    hashed_user_password = hash_password(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_user_password,
        is_active=True  # Default to active, can be changed later if needed
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
