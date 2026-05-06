#!/usr/bin/env python3
"""
Script para crear usuarios desde CSV con formato personalizado
Formato esperado: NAME,EMAIL,ID,PASSWORD,ROLE

Uso:
    python bulk_create_users_custom.py estudiantes.csv
    python bulk_create_users_custom.py estudiantes.csv --dry-run
"""

import sys
import csv
import os
from pathlib import Path

# Agregar directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, User
from app.auth import get_password_hash


def validate_csv_format(csv_path: str) -> bool:
    """Validar que el CSV tiene el formato correcto"""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Verificar headers (aceptar mayúsculas/minúsculas)
            headers = set([h.upper() for h in (reader.fieldnames or [])])
            required_headers = {'NAME', 'EMAIL', 'ID', 'PASSWORD'}
            
            if not required_headers.issubset(headers):
                missing = required_headers - headers
                print(f"❌ ERROR: Faltan columnas requeridas: {missing}")
                print(f"   Columnas encontradas: {headers}")
                print(f"   Columnas requeridas: {required_headers}")
                return False
            
            # Verificar que hay al menos una fila
            rows = list(reader)
            if not rows:
                print("❌ ERROR: El CSV está vacío (no tiene datos)")
                return False
            
            print(f"✅ CSV válido: {len(rows)} usuarios encontrados")
            return True
            
    except FileNotFoundError:
        print(f"❌ ERROR: Archivo no encontrado: {csv_path}")
        return False
    except Exception as e:
        print(f"❌ ERROR al leer CSV: {e}")
        return False


def load_users_from_csv(csv_path: str, dry_run: bool = False) -> dict:
    """
    Cargar usuarios desde CSV personalizado y crearlos en la base de datos
    
    Mapeo de columnas:
    - NAME → full_name
    - EMAIL → email
    - ID → username
    - PASSWORD → password
    - ROLE → is_admin (si ROLE == "ADMIN")
    
    Args:
        csv_path: Ruta al archivo CSV
        dry_run: Si True, solo valida sin crear usuarios
    
    Returns:
        dict con estadísticas de la operación
    """
    db = SessionLocal()
    stats = {
        'total': 0,
        'created': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Normalizar headers a mayúsculas
            normalized_headers = {h.upper(): h for h in reader.fieldnames}
            
            for idx, row in enumerate(reader, start=1):
                stats['total'] += 1
                
                # Mapear columnas (case-insensitive)
                full_name = row.get(normalized_headers.get('NAME', 'NAME'), '').strip()
                email = row.get(normalized_headers.get('EMAIL', 'EMAIL'), '').strip()
                username = row.get(normalized_headers.get('ID', 'ID'), '').strip()
                password = row.get(normalized_headers.get('PASSWORD', 'PASSWORD'), '').strip()
                role = row.get(normalized_headers.get('ROLE', 'ROLE'), 'USER').strip().upper()
                
                # Determinar si es admin
                is_admin = (role == 'ADMIN')
                
                # Validaciones básicas
                if not username or not email or not password:
                    error_msg = f"Fila {idx}: Datos incompletos (ID, EMAIL o PASSWORD vacíos)"
                    print(f"⚠️  {error_msg}")
                    stats['errors'] += 1
                    stats['details'].append({'row': idx, 'status': 'error', 'reason': error_msg})
                    continue
                
                if len(password) < 6:
                    error_msg = f"Fila {idx}: Password muy corta (mínimo 6 caracteres)"
                    print(f"⚠️  {error_msg}")
                    stats['errors'] += 1
                    stats['details'].append({'row': idx, 'status': 'error', 'reason': error_msg})
                    continue
                
                # Verificar si ya existe
                existing_user = db.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()
                
                if existing_user:
                    skip_msg = f"Fila {idx}: Usuario '{username}' o email '{email}' ya existe"
                    print(f"⏭️  {skip_msg}")
                    stats['skipped'] += 1
                    stats['details'].append({'row': idx, 'status': 'skipped', 'reason': skip_msg})
                    continue
                
                # Modo dry-run: solo validar
                if dry_run:
                    role_display = " [ADMIN]" if is_admin else ""
                    print(f"✓  Fila {idx}: {username} ({email}) - {full_name}{role_display} - VÁLIDO")
                    stats['created'] += 1
                    stats['details'].append({
                        'row': idx,
                        'status': 'valid',
                        'username': username,
                        'is_admin': is_admin
                    })
                    continue
                
                # Crear usuario
                try:
                    new_user = User(
                        username=username,
                        email=email,
                        full_name=full_name if full_name else username,
                        hashed_password=get_password_hash(password),
                        is_admin=is_admin
                    )
                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)
                    
                    role_display = " [ADMIN]" if is_admin else ""
                    print(f"✅ Fila {idx}: Usuario '{username}' creado{role_display} (ID: {new_user.id})")
                    stats['created'] += 1
                    stats['details'].append({
                        'row': idx,
                        'status': 'created',
                        'username': username,
                        'user_id': new_user.id,
                        'is_admin': is_admin
                    })
                    
                except Exception as e:
                    db.rollback()
                    error_msg = f"Fila {idx}: Error al crear '{username}': {str(e)}"
                    print(f"❌ {error_msg}")
                    stats['errors'] += 1
                    stats['details'].append({'row': idx, 'status': 'error', 'reason': error_msg})
    
    except Exception as e:
        print(f"❌ ERROR FATAL al procesar CSV: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    return stats


def print_summary(stats: dict, dry_run: bool = False):
    """Imprimir resumen de la operación"""
    print("\n" + "="*60)
    print("📊 RESUMEN DE LA OPERACIÓN")
    print("="*60)
    
    if dry_run:
        print("🔍 MODO DRY-RUN (no se crearon usuarios realmente)")
    
    print(f"\n📝 Total de filas procesadas: {stats['total']}")
    print(f"✅ Usuarios creados/válidos: {stats['created']}")
    print(f"⏭️  Usuarios omitidos (ya existían): {stats['skipped']}")
    print(f"❌ Errores: {stats['errors']}")
    
    # Contar admins
    admins = len([d for d in stats['details'] if d.get('is_admin')])
    if admins > 0:
        print(f"\n👑 Usuarios ADMIN creados: {admins}")
    
    if stats['created'] > 0:
        print(f"\n{'🎉' if not dry_run else '✓'} {stats['created']} usuarios {'creados' if not dry_run else 'validados'} exitosamente")
    
    if stats['errors'] > 0:
        print(f"\n⚠️  Hubo {stats['errors']} errores. Revisa los mensajes arriba para más detalles.")
    
    print("="*60)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Crear usuarios desde CSV con formato personalizado (NAME,EMAIL,ID,PASSWORD,ROLE)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Formato del CSV:
    NAME,EMAIL,ID,PASSWORD,ROLE
    ARIAS HERNANDEZ ISMAEL,ismaelari224@gmail.com,G01E001,426079613,USER
    ARROYO BECERRIL ALEXIS,alexisagmazz@gmail.com,G01E002,323071581,USER

Mapeo de columnas:
    NAME → full_name (nombre completo del estudiante)
    EMAIL → email (correo electrónico)
    ID → username (identificador único para login)
    PASSWORD → password (contraseña inicial)
    ROLE → is_admin (USER o ADMIN)

Ejemplos:
    # Validar CSV sin crear usuarios
    python bulk_create_users_custom.py estudiantes.csv --dry-run
    
    # Crear usuarios
    python bulk_create_users_custom.py estudiantes.csv
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Ruta al archivo CSV con los usuarios'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Solo validar el CSV sin crear usuarios'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 CARGA MASIVA DE USUARIOS - RAG v2 (Formato Personalizado)")
    print("="*60)
    print(f"Archivo: {args.csv_file}")
    print(f"Modo: {'DRY-RUN (solo validación)' if args.dry_run else 'CREACIÓN REAL'}")
    print("="*60 + "\n")
    
    # Validar formato del CSV
    if not validate_csv_format(args.csv_file):
        sys.exit(1)
    
    print()
    
    # Cargar usuarios
    stats = load_users_from_csv(args.csv_file, dry_run=args.dry_run)
    
    # Mostrar resumen
    print_summary(stats, dry_run=args.dry_run)
    
    # Exit code
    if stats['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()