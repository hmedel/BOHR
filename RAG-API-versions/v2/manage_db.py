#!/usr/bin/env python3
"""
Script de gestión de la base de datos del sistema RAG v2
Permite crear usuarios, limpiar conversaciones y administrar la BD
"""
import sys
import os
from pathlib import Path
from getpass import getpass
from datetime import datetime

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, User, Conversation, Message, Exam, ExamResponse, ExamResult, QueryLog, StudentProgress
from app.auth import get_password_hash
from sqlalchemy import func


def create_user():
    """Crear un nuevo usuario"""
    print("\n=== CREAR NUEVO USUARIO ===")
    username = input("Usuario: ").strip()
    email = input("Email: ").strip()
    full_name = input("Nombre completo: ").strip()
    password = getpass("Contraseña: ")
    password_confirm = getpass("Confirmar contraseña: ")
    
    if password != password_confirm:
        print("❌ Las contraseñas no coinciden")
        return
    
    db = SessionLocal()
    try:
        # Verificar si ya existe
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            print(f"❌ Ya existe un usuario con ese username o email")
            return
        
        # Crear usuario
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Usuario creado exitosamente:")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Nombre: {user.full_name}")
        
    except Exception as e:
        print(f"❌ Error al crear usuario: {e}")
        db.rollback()
    finally:
        db.close()


def list_users():
    """Listar todos los usuarios"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        
        if not users:
            print("\n📋 No hay usuarios registrados")
            return
        
        print(f"\n📋 USUARIOS REGISTRADOS ({len(users)}):")
        print("-" * 80)
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Nombre completo':<25}")
        print("-" * 80)
        
        for user in users:
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {user.full_name or 'N/A':<25}")
        
        # Estadísticas
        print("\n📊 ESTADÍSTICAS:")
        for user in users:
            conv_count = db.query(Conversation).filter(Conversation.user_id == user.id).count()
            msg_count = db.query(Message).join(Conversation).filter(Conversation.user_id == user.id).count()
            print(f"   {user.username}: {conv_count} conversaciones, {msg_count} mensajes")
        
    finally:
        db.close()


def delete_user():
    """Eliminar un usuario y todos sus datos"""
    list_users()
    
    print("\n=== ELIMINAR USUARIO ===")
    user_id = input("ID del usuario a eliminar (o 'cancelar'): ").strip()
    
    if user_id.lower() == 'cancelar':
        return
    
    try:
        user_id = int(user_id)
    except ValueError:
        print("❌ ID inválido")
        return
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"❌ No se encontró usuario con ID {user_id}")
            return
        
        confirm = input(f"⚠️  ¿Eliminar usuario '{user.username}' y TODOS sus datos? (escribe 'ELIMINAR'): ")
        
        if confirm != 'ELIMINAR':
            print("❌ Cancelado")
            return
        
        # Eliminar en orden para respetar foreign keys
        # 1. Exam responses y results
        db.query(ExamResponse).filter(ExamResponse.user_id == user_id).delete()
        db.query(ExamResult).filter(ExamResult.user_id == user_id).delete()
        
        # 2. Exámenes
        db.query(Exam).filter(Exam.user_id == user_id).delete()
        
        # 3. Query logs y student progress
        db.query(QueryLog).filter(QueryLog.user_id == user_id).delete()
        db.query(StudentProgress).filter(StudentProgress.user_id == user_id).delete()
        
        # 4. Mensajes (a través de conversaciones)
        conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
        for conv in conversations:
            db.query(Message).filter(Message.conversation_id == conv.id).delete()
        
        # 5. Conversaciones
        db.query(Conversation).filter(Conversation.user_id == user_id).delete()
        
        # 6. Usuario
        db.delete(user)
        
        db.commit()
        print(f"✅ Usuario '{user.username}' eliminado exitosamente")
        
    except Exception as e:
        print(f"❌ Error al eliminar usuario: {e}")
        db.rollback()
    finally:
        db.close()


def clean_conversations():
    """Limpiar conversaciones de un usuario o todas"""
    print("\n=== LIMPIAR CONVERSACIONES ===")
    print("1. Limpiar conversaciones de un usuario específico")
    print("2. Limpiar TODAS las conversaciones del sistema")
    print("3. Cancelar")
    
    option = input("Opción: ").strip()
    
    db = SessionLocal()
    try:
        if option == '1':
            list_users()
            user_id = input("\nID del usuario: ").strip()
            try:
                user_id = int(user_id)
            except ValueError:
                print("❌ ID inválido")
                return
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"❌ No se encontró usuario con ID {user_id}")
                return
            
            conv_count = db.query(Conversation).filter(Conversation.user_id == user_id).count()
            
            confirm = input(f"⚠️  ¿Eliminar {conv_count} conversaciones de '{user.username}'? (S/N): ")
            if confirm.upper() != 'S':
                print("❌ Cancelado")
                return
            
            # Eliminar mensajes primero
            conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
            for conv in conversations:
                db.query(Message).filter(Message.conversation_id == conv.id).delete()
            
            # Eliminar conversaciones
            db.query(Conversation).filter(Conversation.user_id == user_id).delete()
            db.commit()
            
            print(f"✅ {conv_count} conversaciones eliminadas")
            
        elif option == '2':
            conv_count = db.query(Conversation).count()
            msg_count = db.query(Message).count()
            
            confirm = input(f"⚠️  ¿ELIMINAR TODAS las conversaciones ({conv_count}) y mensajes ({msg_count})? (escribe 'ELIMINAR TODO'): ")
            if confirm != 'ELIMINAR TODO':
                print("❌ Cancelado")
                return
            
            db.query(Message).delete()
            db.query(Conversation).delete()
            db.commit()
            
            print(f"✅ Todas las conversaciones eliminadas ({conv_count} conversaciones, {msg_count} mensajes)")
        
        else:
            print("❌ Cancelado")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def database_stats():
    """Mostrar estadísticas de la base de datos"""
    db = SessionLocal()
    try:
        print("\n📊 ESTADÍSTICAS DE LA BASE DE DATOS")
        print("=" * 60)
        
        # Usuarios
        user_count = db.query(User).count()
        print(f"\n👥 Usuarios: {user_count}")
        
        # Conversaciones
        conv_count = db.query(Conversation).count()
        print(f"💬 Conversaciones: {conv_count}")
        
        # Mensajes
        msg_count = db.query(Message).count()
        user_msg_count = db.query(Message).filter(Message.role == 'user').count()
        assistant_msg_count = db.query(Message).filter(Message.role == 'assistant').count()
        print(f"📝 Mensajes totales: {msg_count}")
        print(f"   - Usuario: {user_msg_count}")
        print(f"   - Asistente: {assistant_msg_count}")
        
        # Exámenes
        exam_count = db.query(Exam).count()
        completed_exams = db.query(Exam).filter(Exam.status == 'completed').count()
        print(f"\n📋 Exámenes: {exam_count}")
        print(f"   - Completados: {completed_exams}")
        
        # Query logs
        query_count = db.query(QueryLog).count()
        if query_count > 0:
            avg_time = db.query(func.avg(QueryLog.response_time)).scalar()
            print(f"\n⏱️  Queries registrados: {query_count}")
            print(f"   - Tiempo promedio: {avg_time:.2f}s")
        
        # Mensajes con feedback
        positive_feedback = db.query(Message).filter(Message.feedback == 1).count()
        negative_feedback = db.query(Message).filter(Message.feedback == -1).count()
        print(f"\n👍 Feedback:")
        print(f"   - Positivo: {positive_feedback}")
        print(f"   - Negativo: {negative_feedback}")
        
    finally:
        db.close()


def main_menu():
    """Menú principal"""
    while True:
        print("\n" + "=" * 60)
        print("🔧 GESTIÓN DE BASE DE DATOS - RAG SYSTEM v2")
        print("=" * 60)
        print("\n1. Crear nuevo usuario")
        print("2. Listar usuarios")
        print("3. Eliminar usuario")
        print("4. Limpiar conversaciones")
        print("5. Estadísticas de la base de datos")
        print("6. Salir")
        
        choice = input("\nOpción: ").strip()
        
        if choice == '1':
            create_user()
        elif choice == '2':
            list_users()
        elif choice == '3':
            delete_user()
        elif choice == '4':
            clean_conversations()
        elif choice == '5':
            database_stats()
        elif choice == '6':
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    print("\n🚀 Iniciando gestor de base de datos...")
    
    # Verificar que existe la base de datos
    db_path = Path(__file__).parent / "data" / "rag_system.db"
    if not db_path.exists():
        print(f"⚠️  Advertencia: No se encontró la base de datos en {db_path}")
        print("   Se creará al ejecutar operaciones")
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por el usuario. ¡Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()