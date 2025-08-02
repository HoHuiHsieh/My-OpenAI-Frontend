"""
Admin management endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..user_management import UserManager, User, UserCreate, UserUpdate
from .middleware import get_admin_user, get_db

# Initialize user manager
user_manager = UserManager()

# Create router
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/users", response_model=List[User])
async def list_users(
    skip: int = 0, 
    limit: int = 100,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only)
    """
    users = user_manager.get_users(db, skip=skip, limit=limit)
    return users


@admin_router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only)
    """
    # Check if user already exists
    existing_user = user_manager.get_user(db, username=user_create.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    return user_manager.create_user(db, user_create)


@admin_router.get("/users/{username}", response_model=User)
async def get_user(
    username: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user by username (admin only)
    """
    user = user_manager.get_user(db, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@admin_router.put("/users/{username}", response_model=User)
async def update_user(
    username: str,
    user_update: UserUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user by username (admin only)
    """
    updated_user = user_manager.update_user(db, username, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user


@admin_router.delete("/users/{username}")
async def delete_user(
    username: str,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete user by username (admin only)
    """
    success = user_manager.delete_user(db, username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"detail": "User deleted successfully"}
