#!/usr/bin/env python3
"""
Skrypt do tworzenia administratora i inicjalizacji podstawowych danych
Uruchom jako: python app/create_admin.py
"""

import sys
import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.models import User, UserRole, UserRank, UserRoleEnum, UserRankEnum, Base

# Create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_admin_input():
    """Pobiera dane administratora - z ENV lub od użytkownika"""
    print("\n🔧 Konfiguracja administratora")
    print("=" * 40)
    
    # Check environment variables first
    username = os.getenv('ADMIN_USERNAME')
    email = os.getenv('ADMIN_EMAIL') 
    password = os.getenv('ADMIN_PASSWORD')
    full_name = os.getenv('ADMIN_FULL_NAME')
    
    # If not in environment, ask user
    if not username:
        username = input("👤 Username administratora [admin]: ").strip() or "admin"
    else:
        print(f"👤 Username (z ENV): {username}")
        
    if not email:
        email = input("📧 Email administratora [admin@example.com]: ").strip() or "admin@example.com"
    else:
        print(f"📧 Email (z ENV): {email}")
        
    if not password:
        password = input("🔑 Hasło administratora [admin123]: ").strip() or "admin123"
    else:
        print(f"🔑 Hasło (z ENV): {'*' * len(password)}")
        
    if not full_name:
        full_name = input("📝 Pełne imię [Administrator]: ").strip() or "Administrator"
    else:
        print(f"📝 Pełne imię (z ENV): {full_name}")
    
    return username, email, password, full_name

def create_admin_user():
    """Create the first admin user with data initialization"""
    
    print("🚀 Portfolio Backend - Inicjalizacja administratora")
    print("=" * 50)
    
    print("🏗️  Przygotowywanie bazy danych...")
    
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Always initialize basic data
    print("🌱 Inicjalizacja podstawowych danych...")
    
    print("🌍 Inicjalizacja języków...")
    from app.database import init_roles_and_ranks, init_default_languages
    init_default_languages()
    
    print("👥 Inicjalizacja ról i rang...")
    init_roles_and_ranks()
    
    print("✅ Podstawowe dane zainicjalizowane!")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.is_admin == True).first()
        
        if admin_user:
            print(f"✅ Admin już istnieje: {admin_user.username} ({admin_user.email})")
            print(f"   Ranga: {admin_user.rank.display_name if admin_user.rank else 'Brak'}")
            print(f"   Rola: {admin_user.role.display_name if admin_user.role else 'Brak'}")
            return admin_user
        
        # Get admin details
        print("👑 Tworzenie pierwszego administratora...")
        
        username, email, password, full_name = get_admin_input()
        
        # Validate input
        if not username or not email or not password:
            print("❌ Nazwa użytkownika, email i hasło są wymagane!")
            return None
        
        # Check if user with same username or email exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print("❌ Użytkownik z taką nazwą lub emailem już istnieje!")
            return existing_user
        
        # Hash password
        hashed_password = pwd_context.hash(password)
        
        # Get admin role and VIP rank (highest rank for admin)
        admin_role = db.query(UserRole).filter(UserRole.name == UserRoleEnum.ADMIN).first()
        vip_rank = db.query(UserRank).filter(UserRank.name == UserRankEnum.VIP).first()
        
        if not admin_role:
            print("❌ Rola administratora nie została znaleziona! Upewnij się że inicjalizacja przebiegła pomyślnie.")
            return None
            
        if not vip_rank:
            print("❌ Ranga VIP nie została znaleziona! Upewnij się że inicjalizacja przebiegła pomyślnie.")
            # Fallback to any available rank
            vip_rank = db.query(UserRank).first()
            if vip_rank:
                print(f"⚠️  Używam dostępnej rangi: {vip_rank.display_name}")
        
        # Create admin user
        print("🔐 Tworzenie konta administratora...")
        admin_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_admin=True,
            email_verified=True,  # Auto-verify admin email
            role_id=admin_role.id,  # Przypisz rolę administratora
            rank_id=vip_rank.id if vip_rank else None  # Przypisz najwyższą rangę
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"🎉 Konto administratora zostało utworzone pomyślnie!")
        print(f"👤 Nazwa użytkownika: {admin_user.username}")
        print(f"📧 Email: {admin_user.email}")
        print(f"🆔 ID użytkownika: {admin_user.id}")
        print(f"🏷️  Rola: {admin_role.display_name}")
        print(f"⭐ Ranga: {vip_rank.display_name if vip_rank else 'Brak'}")
        print(f"\n🚀 Możesz się teraz zalogować do panelu administracyjnego używając tych danych.")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def main():
    """Main function for script execution"""
    print("🚀 Portfolio Backend - Inicjalizacja systemu")
    print("=" * 50)
    
    create_admin_user()

if __name__ == "__main__":
    main()
