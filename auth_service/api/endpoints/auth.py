from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...db.dependencies import get_db
from ...schemas.user import UserCreate, UserRead
from ...schemas.token import Token, RefreshTokenRequest, NewAccessTokenResponse # Updated imports
from ...crud import crud_user
from ...core.security import ( # Updated imports
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    decode_token
)
# from ...models.models import User # Not strictly needed if crud returns User model instance

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    """
    db_user_by_email = crud_user.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    db_user_by_username = crud_user.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken."
        )
        
    created_user = crud_user.create_user(db=db, user=user)
    return created_user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud_user.get_user_by_username(db, username=form_data.username)
    if not user or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Using username as subject for the token, could also be user.id
    access_token_data = {"sub": user.username}
    access_token = create_access_token(data=access_token_data)
    
    refresh_token_data = {"sub": user.username} # Keep subject the same for refresh
    refresh_token = create_refresh_token(data=refresh_token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.post("/token/refresh", response_model=NewAccessTokenResponse)
async def refresh_access_token(
    request_body: RefreshTokenRequest, 
    db: Session = Depends(get_db)
):
    """
    Refresh an access token using a valid refresh token.
    """
    token_data = decode_token(request_body.refresh_token)
    
    if not token_data or not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = crud_user.get_user_by_username(db, username=token_data.sub)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Create a new access token
    new_access_token_data = {"sub": user.username}
    new_access_token = create_access_token(data=new_access_token_data)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }
