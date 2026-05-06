#!/usr/bin/env python3
"""
Script para limpiar la base de datos SQLite del sistema RAG v2

Opciones de limpieza:
1. Limpiar todo (RESET COMPLETO)
2. Limpiar solo conversaciones y mensajes
3. Limpiar solo exámenes
4. Limpiar solo usuarios (excepto admin)
5. Limpiar analytics (query_logs, student_progress)
6. Backup antes de limpiar
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
import shutil

# Directorio del proyecto
PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data" / "rag_system.db"
BACKUP_DIR = PROJECT_DIR / "data" / "backups"


def create_backup(db_path: Path) -> Path:
    """Crea backup de la base de datos"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"rag_system_backup_{timestamp}.db"
    
    print(f"📦 Creando backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup creado exitosamente")
    return backup_path


def get_table_counts(conn: sqlite3.Connection) -> dict:
    """Obtiene el conteo de registros por tabla"""
    cursor = conn.cursor()
    tables = [
        "users", "conversations", "messages", "query_logs",
        "student_progress", "exams", "exam_responses", "exam_results"
    ]
    
    counts = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    
    return counts


def clean_all(conn: sqlite3.Connection, keep_admin: bool = True):
    """Limpia TODA la base de datos (RESET COMPLETO)"""
    cursor = conn.cursor()
    
    print("\n🔴 LIMPIEZA TOTAL DE LA BASE DE DATOS")
    print("=" * 60)
    
    # Orden correcto por foreign keys
    tables_order = [
        "exam_results",
        "exam_responses", 
        "exams",
        "messages",
        "conversations",
        "query_logs",
        "student_progress"
    ]
    
    for table in tables_order:
        cursor.execute(f"DELETE FROM {table}")
        print(f"✅ Tabla '{table}' limpiada")
    
    # Limpiar usuarios (opcionalmente mantener admin)
    if keep_admin:
        cursor.execute("DELETE FROM users WHERE is_admin = 0")
        print(f"✅ Usuarios no-admin eliminados")
    else:
        cursor.execute("DELETE FROM users")
        print(f"✅ TODOS los usuarios eliminados")
    
    conn.commit()
    print("\n✅ Limpieza total completada")


def clean_conversations(conn: sqlite3.Connection):
    """Limpia solo conversaciones y mensajes"""
    cursor = conn.cursor()
    
    print("\n🧹 Limpiando conversaciones y mensajes...")
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM conversations")
    conn.commit()
    print("✅ Conversaciones y mensajes eliminados")


def clean_exams(conn: sqlite3.Connection):
    """Limpia solo exámenes y respuestas"""
    cursor = conn.cursor()
    
    print("\n📝 Limpiando exámenes...")
    cursor.execute("DELETE FROM exam_results")
    cursor.execute("DELETE FROM exam_responses")
    cursor.execute("DELETE FROM exams")
    conn.commit()
    print("✅ Exámenes eliminados")


def clean_users(conn: sqlite3.Connection, keep_admin: bool = True):
    """Limpia usuarios (opcionalmente mantiene admin)"""
    cursor = conn.cursor()
    
    print("\n👥 Limpiando usuarios...")
    
    # Primero limpiar todas las tablas relacionadas
    cursor.execute("DELETE FROM exam_results")
    cursor.execute("DELETE FROM exam_responses")
    cursor.execute("DELETE FROM exams")
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM conversations")
    cursor.execute("DELETE FROM query_logs")
    cursor.execute("DELETE FROM student_progress")
    
    # Luego usuarios
    if keep_admin:
        cursor.execute("DELETE FROM users WHERE is_admin = 0")
        remaining = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print(f"✅ Usuarios no-admin eliminados (quedan {remaining} admins)")
    else:
        cursor.execute("DELETE FROM users")
        print("✅ TODOS los usuarios eliminados")
    
    conn.commit()


def clean_analytics(conn: sqlite3.Connection):
    """Limpia solo datos de analytics"""
    cursor = conn.cursor()
    
    print("\n📊 Limpiando analytics...")
    cursor.execute("DELETE FROM query_logs")
    cursor.execute("DELETE FROM student_progress")
    conn.commit()
    print("✅ Analytics eliminados")


def reset_autoincrement(conn: sqlite3.Connection):
    """Resetea los contadores de auto-incremento"""
    cursor = conn.cursor()
    
    print("\n🔄 Reseteando contadores de auto-incremento...")
    cursor.execute("DELETE FROM sqlite_sequence")
    conn.commit()
    print("✅ Contadores reseteados")


def show_statistics(db_path: Path):
    """Muestra estadísticas de la base de datos"""
    if not db_path.exists():
        print(f"⚠️  Base de datos no encontrada: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    counts = get_table_counts(conn)
    
    print("\n📊 ESTADÍSTICAS DE LA BASE DE DATOS")
    print("=" * 60)
    print(f"Ruta: {db_path}")
    print(f"Tamaño: {db_path.stat().st_size / 1024:.2f} KB")
    print("\nRegistros por tabla:")
    print("-" * 60)
    
    for table, count in counts.items():
        print(f"  {table:20s}: {count:6d} registros")
    
    total = sum(counts.values())
    print("-" * 60)
    print(f"  {'TOTAL':20s}: {total:6d} registros")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Script para limpiar la base de datos SQLite del sistema RAG v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Ver estadísticas sin limpiar
  python clean_database.py --stats
  
  # Limpieza completa con backup automático
  python clean_database.py --all
  
  # Limpiar solo conversaciones
  python clean_database.py --conversations
  
  # Limpiar usuarios (mantener admin)
  python clean_database.py --users --keep-admin
  
  # Limpiar todo incluyendo admin
  python clean_database.py --all --no-keep-admin
  
  # Sin backup (¡PELIGROSO!)
  python clean_database.py --all --no-backup
        """
    )
    
    # Opciones de limpieza
    parser.add_argument("--all", action="store_true", help="Limpiar TODA la base de datos")
    parser.add_argument("--conversations", action="store_true", help="Limpiar solo conversaciones")
    parser.add_argument("--exams", action="store_true", help="Limpiar solo exámenes")
    parser.add_argument("--users", action="store_true", help="Limpiar usuarios")
    parser.add_argument("--analytics", action="store_true", help="Limpiar analytics")
    
    # Opciones de configuración
    parser.add_argument("--keep-admin", action="store_true", default=True, 
                       help="Mantener usuarios admin (default: True)")
    parser.add_argument("--no-keep-admin", action="store_false", dest="keep_admin",
                       help="Eliminar TODOS los usuarios incluyendo admin")
    parser.add_argument("--backup", action="store_true", default=True,
                       help="Crear backup antes de limpiar (default: True)")
    parser.add_argument("--no-backup", action="store_false", dest="backup",
                       help="NO crear backup (¡PELIGROSO!)")
    parser.add_argument("--stats", action="store_true", help="Solo mostrar estadísticas")
    parser.add_argument("--reset-autoincrement", action="store_true",
                       help="Resetear contadores de auto-incremento")
    
    args = parser.parse_args()
    
    # Verificar que la base de datos existe
    if not DB_PATH.exists():
        print(f"❌ Error: Base de datos no encontrada en {DB_PATH}")
        sys.exit(1)
    
    # Solo mostrar estadísticas
    if args.stats:
        show_statistics(DB_PATH)
        return
    
    # Verificar que se seleccionó al menos una opción de limpieza
    cleaning_options = [args.all, args.conversations, args.exams, args.users, args.analytics]
    if not any(cleaning_options):
        print("❌ Error: Debes especificar al menos una opción de limpieza")
        print("Usa --help para ver las opciones disponibles")
        sys.exit(1)
    
    # Mostrar estadísticas antes
    print("\n📊 ANTES DE LIMPIAR:")
    show_statistics(DB_PATH)
    
    # Confirmar acción
    print("\n⚠️  ADVERTENCIA: Esta acción eliminará datos permanentemente")
    if args.all:
        print("🔴 LIMPIEZA TOTAL SELECCIONADA")
    
    response = input("\n¿Continuar? (escribe 'SI' para confirmar): ")
    if response != "SI":
        print("❌ Operación cancelada")
        sys.exit(0)
    
    # Crear backup si está habilitado
    if args.backup:
        create_backup(DB_PATH)
    else:
        print("⚠️  Ejecutando SIN backup")
    
    # Conectar a la base de datos
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Ejecutar limpieza según opciones
        if args.all:
            clean_all(conn, keep_admin=args.keep_admin)
        else:
            if args.conversations:
                clean_conversations(conn)
            if args.exams:
                clean_exams(conn)
            if args.users:
                clean_users(conn, keep_admin=args.keep_admin)
            if args.analytics:
                clean_analytics(conn)
        
        # Resetear auto-increment si se solicita
        if args.reset_autoincrement:
            reset_autoincrement(conn)
        
        # Mostrar estadísticas después
        print("\n📊 DESPUÉS DE LIMPIAR:")
        show_statistics(DB_PATH)
        
        print("\n✅ Limpieza completada exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error durante la limpieza: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()