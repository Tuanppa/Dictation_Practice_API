#!/usr/bin/env python3
"""
Script để xem users trong database
Chạy: python view_users.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from sqlalchemy import func

def view_all_users():
    """Xem tất cả users"""
    print("\n" + "=" * 100)
    print("👥 ALL USERS IN DATABASE")
    print("=" * 100)
    
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("\n⚠️  No users found in database")
            return
        
        print(f"\n📊 Total users: {len(users)}\n")
        
        for user in users:
            print(f"{'─' * 100}")
            print(f"ID:              {user.id}")
            print(f"Email:           {user.email}")
            print(f"Full Name:       {user.full_name or 'N/A'}")
            print(f"Phone:           {user.phone_number or 'N/A'}")
            print(f"Date of Birth:   {user.date_of_birth or 'N/A'}")
            print(f"Gender:          {user.gender.value if user.gender else 'N/A'}")
            print(f"Auth Provider:   {user.auth_provider.value}")
            print(f"Role:            {user.role.value}")
            print(f"Is Premium:      {'✅ Yes' if user.is_premium else '❌ No'}")
            if user.is_premium:
                print(f"Premium Start:   {user.premium_start_date or 'N/A'}")
                print(f"Premium End:     {user.premium_end_date or 'N/A'}")
            print(f"Is Active:       {'✅ Yes' if user.is_active else '❌ No'}")
            print(f"Is Verified:     {'✅ Yes' if user.is_verified else '❌ No'}")
            print(f"Created At:      {user.created_at}")
            print(f"Last Login:      {user.last_login or 'Never'}")
        
        print(f"{'─' * 100}\n")
        
    finally:
        db.close()

def view_user_by_email(email: str):
    """Xem user theo email"""
    print(f"\n🔍 Searching for user: {email}")
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print(f"\n✅ User found!")
        print(f"{'─' * 80}")
        print(f"ID:              {user.id}")
        print(f"Email:           {user.email}")
        print(f"Full Name:       {user.full_name or 'N/A'}")
        print(f"Phone:           {user.phone_number or 'N/A'}")
        print(f"Auth Provider:   {user.auth_provider.value}")
        print(f"Role:            {user.role.value}")
        print(f"Is Premium:      {'✅ Yes' if user.is_premium else '❌ No'}")
        print(f"Created At:      {user.created_at}")
        print(f"Last Login:      {user.last_login or 'Never'}")
        print(f"{'─' * 80}\n")
        
    finally:
        db.close()

def view_statistics():
    """Xem thống kê users"""
    print("\n" + "=" * 80)
    print("📊 USER STATISTICS")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        total = db.query(func.count(User.id)).scalar()
        active = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        premium = db.query(func.count(User.id)).filter(User.is_premium == True).scalar()
        verified = db.query(func.count(User.id)).filter(User.is_verified == True).scalar()
        
        print(f"\n📈 Summary:")
        print(f"   Total Users:      {total}")
        print(f"   Active Users:     {active}")
        print(f"   Premium Users:    {premium}")
        print(f"   Verified Users:   {verified}")
        
        # Auth providers
        from app.models.user import AuthProviderEnum
        print(f"\n🔐 By Auth Provider:")
        for provider in AuthProviderEnum:
            count = db.query(func.count(User.id)).filter(User.auth_provider == provider).scalar()
            print(f"   {provider.value.capitalize():12} {count}")
        
        # Roles
        from app.models.user import RoleEnum
        print(f"\n👤 By Role:")
        for role in RoleEnum:
            count = db.query(func.count(User.id)).filter(User.role == role).scalar()
            print(f"   {role.value.capitalize():12} {count}")
        
        print(f"\n{'─' * 80}\n")
        
    finally:
        db.close()

def view_recent_users(limit: int = 5):
    """Xem users mới đăng ký gần đây"""
    print(f"\n" + "=" * 80)
    print(f"🆕 {limit} MOST RECENT USERS")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
        
        if not users:
            print("\n⚠️  No users found")
            return
        
        print()
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.email:30} | {user.full_name or 'N/A':20} | {user.created_at}")
        
        print()
        
    finally:
        db.close()

def delete_user_by_email(email: str):
    """Xóa user theo email"""
    print(f"\n⚠️  WARNING: Deleting user: {email}")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        db.delete(user)
        db.commit()
        print(f"✅ User deleted: {email}")
        
    finally:
        db.close()

def main():
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "DATABASE VIEWER" + " " * 38 + "║")
    print("╚" + "═" * 78 + "╝")
    
    while True:
        print("\n📋 Menu:")
        print("  1. View all users")
        print("  2. View statistics")
        print("  3. View recent users")
        print("  4. Search user by email")
        print("  5. Delete user by email")
        print("  0. Exit")
        
        choice = input("\nSelect option (0-5): ").strip()
        
        if choice == '0':
            print("\n👋 Goodbye!")
            break
        elif choice == '1':
            view_all_users()
        elif choice == '2':
            view_statistics()
        elif choice == '3':
            try:
                limit = int(input("How many users? (default 5): ") or "5")
                view_recent_users(limit)
            except ValueError:
                print("❌ Invalid number")
        elif choice == '4':
            email = input("Enter email: ").strip()
            if email:
                view_user_by_email(email)
        elif choice == '5':
            email = input("Enter email to delete: ").strip()
            if email:
                delete_user_by_email(email)
        else:
            print("❌ Invalid option")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()