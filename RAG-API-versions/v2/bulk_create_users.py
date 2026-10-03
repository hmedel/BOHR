#!/usr/bin/env python3
"""
Script para crear usuarios masivamente desde un archivo CSV

Formato esperado del CSV:
username,email,password,full_name[,role]
juan123,juan@example.com,MiPassword123,Juan Pérez
maria456,maria@example.com,,María García,docente

- password vacío → se genera una aleatoria de 10 caracteres
- role (opcional): "alumno" (default) o "docente". Los docentes usan el chat
  igual que un alumno pero quedan fuera del corpus del estudio (criterio E0).
- Las contraseñas generadas se guardan en un CSV privado (chmod 600) fuera del
  repo; ver --credenciales. No se imprimen en pantalla.

Uso:
    python bulk_create_users.py usuarios.csv
    python bulk_create_users.py usuarios.csv --dry-run  # Solo validar sin crear
"""

import sys
import csv
import os
import secrets
import string
from datetime import datetime
from pathlib import Path

# Agregar directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, User
from app.auth import get_password_hash

CREDENTIALS_DIR = Path.home() / "BOHR_credenciales"
TEACHER_ROLES = {"docente", "profesor", "profesora", "teacher"}
STUDENT_ROLES = {"", "alumno", "alumna", "estudiante", "student"}


def generate_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def validate_csv_format(csv_path: str) -> bool:
    """Validar que el CSV tiene el formato correcto"""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Verificar headers
            required_headers = {'username', 'email', 'full_name'}  # password y role son opcionales
            headers = set(reader.fieldnames or [])
            
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


def load_users_from_csv(csv_path: str, dry_run: bool = False, credentials_path: Path = None) -> dict:
    """
    Cargar usuarios desde CSV y crearlos en la base de datos
    
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
        'details': [],
        'credentials': [],   # (username, full_name, email, password, role) de las cuentas creadas
    }
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for idx, row in enumerate(reader, start=1):
                stats['total'] += 1
                
                username = row['username'].strip()
                email = row['email'].strip()
                password = (row.get('password') or '').strip()
                full_name = row['full_name'].strip()
                role = (row.get('role') or '').strip().lower()

                if role not in TEACHER_ROLES | STUDENT_ROLES:
                    error_msg = f"Fila {idx}: role '{role}' no reconocido (usa alumno o docente)"
                    print(f"⚠️  {error_msg}")
                    stats['errors'] += 1
                    stats['details'].append({'row': idx, 'status': 'error', 'reason': error_msg})
                    continue
                is_teacher = role in TEACHER_ROLES
                if not password:
                    password = generate_password()
                
                # Validaciones básicas
                if not username or not email or not password:
                    error_msg = f"Fila {idx}: Datos incompletos (username, email o password vacíos)"
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
                    print(f"✓  Fila {idx}: {username} ({email}) - VÁLIDO (no creado en modo dry-run)")
                    stats['created'] += 1
                    stats['details'].append({'row': idx, 'status': 'valid', 'username': username})
                    continue
                
                # Crear usuario
                try:
                    new_user = User(
                        username=username,
                        email=email,
                        full_name=full_name,
                        hashed_password=get_password_hash(password),
                        is_admin=False,
                        is_teacher=is_teacher,
                    )
                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)
                    
                    role_display = " [docente]" if is_teacher else ""
                    print(f"✅ Fila {idx}: Usuario '{username}'{role_display} creado exitosamente (ID: {new_user.id})")
                    stats['created'] += 1
                    stats['credentials'].append((username, full_name, email, password, "docente" if is_teacher else "alumno"))
                    stats['details'].append({
                        'row': idx,
                        'status': 'created',
                        'username': username,
                        'user_id': new_user.id
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

    if stats['credentials'] and not dry_run:
        credentials_path = credentials_path or CREDENTIALS_DIR / f"altas_{datetime.now():%Y%m%d_%H%M%S}.csv"
        credentials_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(credentials_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["usuario", "nombre", "email", "contraseña", "rol"])
            w.writerows(stats['credentials'])
        os.chmod(credentials_path, 0o600)
        stats['credentials_path'] = str(credentials_path)

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
    
    if stats['created'] > 0:
        print(f"\n{'🎉' if not dry_run else '✓'} {stats['created']} usuarios {'creados' if not dry_run else 'validados'} exitosamente")
    
    if stats.get('credentials_path'):
        print(f"\n🔑 Credenciales de las cuentas creadas (archivo privado): {stats['credentials_path']}")

    if stats['errors'] > 0:
        print(f"\n⚠️  Hubo {stats['errors']} errores. Revisa los mensajes arriba para más detalles.")
    
    print("="*60)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Crear usuarios masivamente desde un archivo CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Formato del CSV (password y role opcionales):
    username,email,password,full_name,role
    juan123,juan@example.com,MiPassword123,Juan Pérez,alumno
    maria456,maria@example.com,,María García,docente

Ejemplos:
    # Validar CSV sin crear usuarios
    python bulk_create_users.py usuarios.csv --dry-run
    
    # Crear usuarios
    python bulk_create_users.py usuarios.csv
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Ruta al archivo CSV con los usuarios'
    )
    
    parser.add_argument(
        '--credenciales',
        type=Path,
        default=None,
        help='CSV donde guardar las contraseñas de las cuentas creadas (default: ~/BOHR_credenciales/altas_<fecha>.csv)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Solo validar el CSV sin crear usuarios'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 CARGA MASIVA DE USUARIOS - RAG v2")
    print("="*60)
    print(f"Archivo: {args.csv_file}")
    print(f"Modo: {'DRY-RUN (solo validación)' if args.dry_run else 'CREACIÓN REAL'}")
    print("="*60 + "\n")
    
    # Validar formato del CSV
    if not validate_csv_format(args.csv_file):
        sys.exit(1)
    
    print()
    
    # Cargar usuarios
    stats = load_users_from_csv(args.csv_file, dry_run=args.dry_run, credentials_path=args.credenciales)
    
    # Mostrar resumen
    print_summary(stats, dry_run=args.dry_run)
    
    # Exit code
    if stats['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()