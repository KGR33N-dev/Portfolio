"""
Router dla zarządzania systemem ról i rang użytkowników
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from ..database import get_db
from ..models import User, UserRole, UserRank, UserRoleEnum, UserRankEnum
from ..schemas import UserRole as UserRoleSchema, UserRank as UserRankSchema, UserWithRoleRank
from ..security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/api/roles", tags=["User Roles & Ranks"])

# 🎯 ROLE MANAGEMENT ENDPOINTS

@router.get("/roles", response_model=List[UserRoleSchema])
def get_all_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pobierz wszystkie dostępne role"""
    roles = db.query(UserRole).filter(UserRole.is_active == True).all()
    return roles

@router.get("/ranks", response_model=List[UserRankSchema])
def get_all_ranks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pobierz wszystkie dostępne rangi"""
    ranks = db.query(UserRank).filter(UserRank.is_active == True).order_by(UserRank.level).all()
    return ranks

@router.get("/user/{user_id}", response_model=UserWithRoleRank)
def get_user_role_rank(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pobierz informacje o roli i randze użytkownika"""
    user = db.query(User).options(
        joinedload(User.role),
        joinedload(User.rank)
    ).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Tylko admin lub sam użytkownik może zobaczyć szczegóły
    if current_user.id != user.id and not current_user.has_permission("user.manage"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Dodaj computed fields
    user_data = UserWithRoleRank.from_orm(user)
    user_data.display_role = user.get_display_role()
    user_data.display_rank = user.get_display_rank()
    user_data.role_color = user.get_role_color()
    user_data.rank_icon = user.get_rank_icon()
    
    return user_data

@router.post("/user/{user_id}/role/{role_name}")
def assign_user_role(
    user_id: int,
    role_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Przypisz rolę użytkownikowi (tylko admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(UserRole).filter(UserRole.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    user.role_id = role.id
    
    # Aktualizuj legacy is_admin field
    if role.name == UserRoleEnum.ADMIN:
        user.is_admin = True
    else:
        user.is_admin = False
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Przypisano rolę {role.display_name} użytkownikowi {user.username}"
    }

@router.post("/user/{user_id}/rank/{rank_name}")
def assign_user_rank(
    user_id: int,
    rank_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Przypisz rangę użytkownikowi (tylko admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    rank = db.query(UserRank).filter(UserRank.name == rank_name).first()
    if not rank:
        raise HTTPException(status_code=404, detail="Rank not found")
    
    user.rank_id = rank.id
    db.commit()
    
    return {
        "success": True,
        "message": f"Przypisano rangę {rank.display_name} użytkownikowi {user.username}"
    }

@router.post("/check-rank-upgrade/{user_id}")
def check_rank_upgrade(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sprawdź i automatycznie awansuj rangę użytkownika"""
    user = db.query(User).options(joinedload(User.rank)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Tylko sam użytkownik lub admin
    if current_user.id != user.id and not current_user.has_permission("user.manage"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Znajdź najwyższą rangę którą spełnia
    available_ranks = db.query(UserRank).filter(
        UserRank.is_active == True
    ).order_by(UserRank.level.desc()).all()
    
    upgraded = False
    new_rank = None
    
    for rank in available_ranks:
        requirements = rank.requirements
        comments_req = requirements.get("comments", 0)
        likes_req = requirements.get("likes", 0)
        
        if (user.total_comments >= comments_req and 
            user.total_likes_received >= likes_req):
            if not user.rank or rank.level > user.rank.level:
                user.rank_id = rank.id
                new_rank = rank
                upgraded = True
                break
    
    if upgraded:
        db.commit()
        return {
            "success": True,
            "upgraded": True,
            "new_rank": new_rank.display_name,
            "message": f"🎉 Awansowano na {new_rank.display_name}!"
        }
    else:
        return {
            "success": True,
            "upgraded": False,
            "message": "Brak awansu - kontynuuj aktywność!"
        }

# 🎯 UTILITY ENDPOINTS

@router.get("/permissions")
def get_available_permissions(
    current_user: User = Depends(get_current_admin_user)
):
    """Lista wszystkich dostępnych uprawnień w systemie"""
    return {
        "permissions": [
            "comment.create", "comment.like", "comment.moderate", "comment.delete",
            "post.create", "post.edit", "post.delete", "post.publish",
            "user.manage", "role.manage", "system.admin",
            "profile.edit", "profile.view"
        ],
        "roles": list(UserRoleEnum),
        "ranks": list(UserRankEnum)
    }

@router.get("/my-profile", response_model=UserWithRoleRank)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pobierz własny profil z rolą i rangą"""
    user = db.query(User).options(
        joinedload(User.role),
        joinedload(User.rank)
    ).filter(User.id == current_user.id).first()
    
    user_data = UserWithRoleRank.from_orm(user)
    user_data.display_role = user.get_display_role()
    user_data.display_rank = user.get_display_rank()
    user_data.role_color = user.get_role_color()
    user_data.rank_icon = user.get_rank_icon()
    
    return user_data
