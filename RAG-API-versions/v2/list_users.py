#!/usr/bin/env python3
"""
Script para listar todos los usuarios de la base de datos SQLite del sistema RAG v2
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# Directorio del proyecto
PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data" / "rag_system.db"


def format_table(headers, rows):
    """Formatea una tabla simple sin dependencias externas"""
    # Calcular anchos de columnas
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Crear línea separadora
    separator = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    
    # Formatear header
    header_row = "| " + " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths)) + " |"
    
    # Formatear filas
    data_rows = []
    for row in rows:
        data_rows.append("| " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths)) + " |")
    
    # Construir tabla
    table = [separator, header_row, separator]
    table.extend(data_rows)
    table.append(separator)
    
    return "\n".join(table)


def list_users(db_path: Path, show_details: bool = False, admin_only: bool = False):
    """Lista todos los usuarios de la base de datos"""
    
    if not db_path.exists():
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query base
    query = """
        SELECT 
            id, 
            username, 
            email, 
            full_name,
            is_admin,
            created_at
        FROM users
    """
    
    # Filtrar solo admins si se solicita
    if admin_only:
        query += " WHERE is_admin = 1"
    
    query += " ORDER BY id ASC"
    
    cursor.execute(query)
    users = cursor.fetchall()
    
    if not users:
        print("⚠️  No hay usuarios en la base de datos")
        conn.close()
        return
    
    # Preparar datos para la tabla
    headers = ["ID", "Usuario", "Email", "Nombre Completo", "Admin", "Fecha Creación"]
    table_data = []
    
    for user in users:
        user_id, username, email, full_name, is_admin, created_at = user
        
        # Formatear fecha
        try:
            dt = datetime.fromisoformat(created_at)
            created_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            created_str = created_at
        
        # Admin badge
        admin_badge = "✅" if is_admin else "❌"
        
        table_data.append([
            user_id,
            username,
            email,
            full_name or "N/A",
            admin_badge,
            created_str
        ])
    
    # Imprimir tabla
    print("\n" + "=" * 120)
    print(f"👥 USUARIOS EN LA BASE DE DATOS")
    print("=" * 120)
    print(format_table(headers, table_data))
    print(f"\nTotal: {len(users)} usuario(s)")
    
    # Estadísticas adicionales si se solicita
    if show_details:
        print("\n" + "=" * 100)
        print("📊 ESTADÍSTICAS POR USUARIO")
        print("=" * 100)
        
        for user in users:
            user_id, username, email, full_name, is_admin, created_at = user
            
            print(f"\n🔹 Usuario: {username} (ID: {user_id})")
            print("-" * 100)
            
            # Contar conversaciones
            cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
            conv_count = cursor.fetchone()[0]
            print(f"  Conversaciones: {conv_count}")
            
            # Contar mensajes
            cursor.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)
            """, (user_id,))
            msg_count = cursor.fetchone()[0]
            print(f"  Mensajes: {msg_count}")
            
            # Contar exámenes
            cursor.execute("SELECT COUNT(*) FROM exams WHERE user_id = ?", (user_id,))
            exam_count = cursor.fetchone()[0]
            print(f"  Exámenes: {exam_count}")
            
            # Contar query logs
            cursor.execute("SELECT COUNT(*) FROM query_logs WHERE user_id = ?", (user_id,))
            query_count = cursor.fetchone()[0]
            print(f"  Queries: {query_count}")
            
            # Progreso
            cursor.execute("SELECT * FROM student_progress WHERE user_id = ?", (user_id,))
            progress = cursor.fetchone()
            if progress:
                print(f"  Progreso registrado: ✅")
            else:
                print(f"  Progreso registrado: ❌")
    
    conn.close()


def export_users_csv(db_path: Path, output_file: str = "users_export.csv"):
    """Exporta la lista de usuarios a CSV"""
    
    if not db_path.exists():
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT username, email, full_name, is_admin, created_at
        FROM users
        ORDER BY id ASC
    """)
    users = cursor.fetchall()
    
    output_path = PROJECT_DIR / output_file
    
    with open(output_path, 'w') as f:
        # Header
        f.write("USERNAME,EMAIL,FULL_NAME,IS_ADMIN,CREATED_AT\n")
        
        # Datos
        for user in users:
            username, email, full_name, is_admin, created_at = user
            full_name = full_name or ""
            f.write(f"{username},{email},{full_name},{is_admin},{created_at}\n")
    
    print(f"✅ Usuarios exportados a: {output_path}")
    print(f"Total: {len(users)} usuario(s)")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Script para listar usuarios de la base de datos SQLite del sistema RAG v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Listar todos los usuarios (simple)
  python list_users.py
  
  # Listar con estadísticas detalladas
  python list_users.py --details
  
  # Listar solo administradores
  python list_users.py --admin-only
  
  # Exportar a CSV
  python list_users.py --export
  python list_users.py --export --output mi_export.csv
        """
    )
    
    parser.add_argument("--details", action="store_true", 
                       help="Mostrar estadísticas detalladas por usuario")
    parser.add_argument("--admin-only", action="store_true",
                       help="Mostrar solo usuarios administradores")
    parser.add_argument("--export", action="store_true",
                       help="Exportar usuarios a CSV")
    parser.add_argument("--output", type=str, default="users_export.csv",
                       help="Nombre del archivo CSV de salida (default: users_export.csv)")
    
    args = parser.parse_args()
    
    if args.export:
        export_users_csv(DB_PATH, args.output)
    else:
        list_users(DB_PATH, show_details=args.details, admin_only=args.admin_only)


if __name__ == "__main__":
    main()