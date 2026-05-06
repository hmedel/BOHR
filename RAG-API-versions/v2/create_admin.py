#!/usr/bin/env python3
"""
Script para crear un usuario administrador en la base de datos

Uso:
    python create_admin.py
    python create_admin.py --username admin --email admin@example.com --password adminpass123
"""

import sys
import argparse
from pathlib import Path

# Agregar directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, User
from app.auth import get_password_hash


def create_admin_user(username: str, email: str, password: str, full_name: str = None):
    """
    Crear un usuario administrador
    
    Args:
        username: Nombre de usuario para login
        email: Email del administrador
        password: Contraseña (se hasheará automáticamente)
        full_name: Nombre completo (opcional)
    
    Returns:
        User object si se creó exitosamente, None si hubo error
    """
    db = SessionLocal()
    
    try:
        # Verificar si ya existe
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"⚠️  ERROR: Usuario '{username}' o email '{email}' ya existe")
            print(f"   ID: {existing_user.id}")
            print(f"   Username: {existing_user.username}")
            print(f"   Email: {existing_user.email}")
            print(f"   Is Admin: {existing_user.is_admin}")
            
            # Preguntar si quiere convertirlo en admin
            if not existing_user.is_admin:
                response = input(f"\n¿Convertir '{existing_user.username}' en administrador? (SI/no): ")
                if response == "SI":
                    existing_user.is_admin = True
                    db.commit()
                    print(f"✅ Usuario '{existing_user.username}' convertido a administrador")
                    return existing_user
            
            return None
        
        # Crear nuevo admin
        admin_user = User(
            username=username,
            email=email,
            full_name=full_name or f"Admin {username}",
            hashed_password=get_password_hash(password),
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Usuario administrador creado exitosamente:")
        print(f"   ID: {admin_user.id}")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Full Name: {admin_user.full_name}")
        print(f"   Is Admin: ✅ True")
        
        return admin_user
        
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR al crear administrador: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Crear usuario administrador en RAG v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
    # Crear admin con credenciales por defecto
    python create_admin.py
    
    # Crear admin con credenciales personalizadas
    python create_admin.py --username admin --email admin@example.com --password secure123
    
    # Con nombre completo
    python create_admin.py --username admin --password secure123 --full-name "Administrador Sistema"
        """
    )
    
    parser.add_argument(
        '--username',
        default='admin',
        help='Username para el administrador (default: admin)'
    )
    
    parser.add_argument(
        '--email',
        default='admin@example.com',
        help='Email del administrador (default: admin@example.com)'
    )
    
    parser.add_argument(
        '--password',
        default='admin123',
        help='Password del administrador (default: admin123)'
    )
    
    parser.add_argument(
        '--full-name',
        help='Nombre completo del administrador (opcional)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔐 CREAR USUARIO ADMINISTRADOR - RAG v2")
    print("=" * 60)
    print(f"Username: {args.username}")
    print(f"Email: {args.email}")
    print(f"Password: {'*' * len(args.password)}")
    if args.full_name:
        print(f"Full Name: {args.full_name}")
    print("=" * 60)
    print()
    
    # Validar password
    if len(args.password) < 6:
        print("❌ ERROR: La contraseña debe tener al menos 6 caracteres")
        sys.exit(1)
    
    # Confirmar
    response = input("¿Crear este usuario administrador? (SI/no): ")
    if response != "SI":
        print("❌ Operación cancelada")
        sys.exit(0)
    
    print()
    
    # Crear admin
    admin = create_admin_user(
        username=args.username,
        email=args.email,
        password=args.password,
        full_name=args.full_name
    )
    
    if admin:
        print()
        print("=" * 60)
        print("✅ CREDENCIALES DE ACCESO:")
        print("=" * 60)
        print(f"URL: http://localhost:9000")
        print(f"Username: {admin.username}")
        print(f"Password: {args.password}")
        print("=" * 60)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()