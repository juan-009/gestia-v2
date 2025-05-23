import argparse
import os
import sys

# Adjust sys.path to allow imports from the app module
# This assumes the script is in auth-service/scripts/deploy/
# For auth-service/scripts/deploy/create_admin_user.py, to reach auth-service/
# it's os.path.join(os.path.dirname(__file__), '..', '..')
# Then to get to auth-service/app, it's one more level:
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
# The provided '../../../' would go one level above 'auth-service'.
# Let's adjust it to point to the 'auth-service' directory, assuming 'app' is directly under it.
# If 'auth_service' is the root of the package that contains 'app', and the script is in 'auth-service/scripts/deploy'
# then 'auth-service' itself needs to be on the path, or the parent of 'auth_service.app'
# The structure is auth-service/app/...
# So if script is auth-service/scripts/deploy/create_admin_user.py
# We need to add auth-service/ to sys.path to allow 'from auth_service.app...'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


from sqlalchemy.orm import Session # For type hinting if needed directly
from auth_service.app.infraestructura.persistencia.orm import SessionLocal # init_db removed as per instruction
from auth_service.app.infraestructura.persistencia.repositorios import SQLUserRepository
from auth_service.app.infraestructura.seguridad.hasher import hash_password
from auth_service.app.shared.config.config import settings
from auth_service.app.dominio.modelos import Usuario
from auth_service.app.dominio.value_objects import Email # This is Pydantic's EmailStr
from auth_service.app.dominio.excepciones import UserAlreadyExistsError


def main(email_str: str, password_str: str):
    print(f"Attempting to create admin user: {email_str}")

    try:
        valid_email = Email(email_str) # Pydantic EmailStr will validate
    except ValueError as e:
        print(f"Error: Invalid email format - {e}")
        return

    db_session: Session = SessionLocal() # Explicit type hint for clarity
    user_repo = SQLUserRepository(db_session)

    try:
        existing_user = user_repo.get_by_email(valid_email)
        if existing_user:
            print(f"Error: User with email {valid_email} already exists.")
            # UserAlreadyExistsError could be raised here if preferred
            return 

        hashed_pwd = hash_password(password_str, settings.PASSWORD_PEPPER)
        
        # As per subtask 13, Usuario model has roles: List[str]
        # The current SQLUserRepository.add method, via _map_user_domain_to_orm_dict,
        # does not map this 'roles' field to the ORM layer's relationship.
        # This means the "admin" role string will be in the domain object but not persisted
        # as a RoleTable relationship by the current basic repo.add.
        # This is a known limitation to be addressed in Role Management (P3).
        admin_user_domain = Usuario(
            email=valid_email, 
            hashed_password=hashed_pwd, 
            is_active=True, 
            roles=["admin"] 
        )
        
        # Assuming user_repo.add does NOT commit, as per task instructions.
        created_user_domain_stub = user_repo.add(admin_user_domain) 
        
        # The current SQLUserRepository.add *does* commit.
        # If it didn't, the following would be necessary:
        # db_session.commit()
        # And to get the ID, a refresh would be needed if add didn't return it:
        # db_session.refresh(created_user_orm_object_if_add_returned_it_or_fetched_it)
        # created_user_id = created_user_orm_object.id

        # Since repo.add in P1S6 *does* commit and returns a domain object with ID:
        print(f"Admin user {created_user_domain_stub.email} (ID: {created_user_domain_stub.id}) created successfully.")
        print("Note: The 'admin' role string is set on the domain object, but full role assignment via database relationships will be handled in Role Management (P3).")


    except UserAlreadyExistsError as e: # If repo.add itself raises this (it doesn't currently)
        print(f"Error: {e}")
        db_session.rollback() # Ensure rollback on custom handled error too
    except Exception as e:
        db_session.rollback()
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user for the Auth Service.")
    parser.add_argument("--email", type=str, required=True, help="Admin user's email address.")
    parser.add_argument("--password", type=str, required=True, help="Admin user's password (will be hashed).")
    
    args = parser.parse_args()

    # Optional: Call init_db()
    # As per task, Alembic should handle table creation in prod.
    # For dev, one might run `python -m auth_service.app.infraestructura.persistencia.orm`
    # or include init_db() here if this script is the very first setup step.
    # print("Ensuring database tables exist (for dev setup)...")
    # from auth_service.app.infraestructura.persistencia.orm import init_db
    # init_db() # This would create tables if they don't exist.

    main(args.email, args.password)
