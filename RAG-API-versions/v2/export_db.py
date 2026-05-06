#!/usr/bin/env python3
"""
Script para exportar datos de la base de datos RAG v2
Incluye análisis de sentimiento, exámenes, respuestas y conversaciones
"""

import sqlite3
import pandas as pd
import json
import argparse
from datetime import datetime
from pathlib import Path
import sys

# Configuración
DB_PATH = "./data/rag_system.db"
EXPORT_DIR = "./exports"

def setup_export_directory():
    """Crear directorio de exportación si no existe"""
    Path(EXPORT_DIR).mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR

def get_connection():
    """Obtener conexión a la base de datos"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        sys.exit(1)

def export_users(conn, output_dir):
    """Exportar tabla de usuarios"""
    query = """
    SELECT
        id, username, email, full_name, is_admin, created_at
    FROM users
    ORDER BY created_at DESC
    """
    df = pd.read_sql_query(query, conn)
    output_file = f"{output_dir}/users.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Usuarios exportados: {len(df)} registros → {output_file}")
    return df

def export_conversations(conn, output_dir, user_id=None):
    """Exportar conversaciones"""
    query = """
    SELECT
        c.id, c.user_id, u.username, c.title,
        c.created_at, c.updated_at,
        COUNT(m.id) as message_count
    FROM conversations c
    LEFT JOIN users u ON c.user_id = u.id
    LEFT JOIN messages m ON c.id = m.conversation_id
    """

    if user_id:
        query += f" WHERE c.user_id = {user_id}"

    query += " GROUP BY c.id ORDER BY c.created_at DESC"

    df = pd.read_sql_query(query, conn)
    output_file = f"{output_dir}/conversations.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Conversaciones exportadas: {len(df)} registros → {output_file}")
    return df

def export_messages_with_sentiment(conn, output_dir, user_id=None, conversation_id=None):
    """Exportar mensajes con análisis de sentimiento"""
    query = """
    SELECT
        m.id, m.conversation_id, c.user_id, u.username,
        m.role, m.content, m.sources, m.context_used,
        m.created_at, m.feedback, m.response_time,
        m.sentiment_score, m.sentiment_label,
        m.query_complexity, m.topics,
        m.bloom_level, m.bloom_description,
        m.solo_level, m.solo_characteristics,
        m.qualitative_feedback
    FROM messages m
    LEFT JOIN conversations c ON m.conversation_id = c.id
    LEFT JOIN users u ON c.user_id = u.id
    WHERE 1=1
    """

    if user_id:
        query += f" AND c.user_id = {user_id}"
    if conversation_id:
        query += f" AND m.conversation_id = {conversation_id}"

    query += " ORDER BY m.created_at ASC"

    df = pd.read_sql_query(query, conn)
    output_file = f"{output_dir}/messages_sentiment.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Mensajes con sentimiento exportados: {len(df)} registros → {output_file}")

    # Exportar también en formato JSON para preservar estructuras complejas
    output_json = f"{output_dir}/messages_sentiment.json"
    df.to_json(output_json, orient='records', indent=2, date_format='iso')
    print(f"✓ Mensajes JSON exportados → {output_json}")

    return df

def export_exams(conn, output_dir, user_id=None):
    """Exportar exámenes generados"""
    query = """
    SELECT
        e.id, e.user_id, u.username,
        e.title, e.exam_data, e.exam_type,
        e.status, e.topics_covered, e.total_questions,
        e.created_at, e.completed_at,
        COUNT(er.id) as response_count
    FROM exams e
    LEFT JOIN users u ON e.user_id = u.id
    LEFT JOIN exam_responses er ON e.id = er.exam_id
    WHERE 1=1
    """

    if user_id:
        query += f" AND e.user_id = {user_id}"

    query += " GROUP BY e.id ORDER BY e.created_at DESC"

    df = pd.read_sql_query(query, conn)

    # Guardar CSV sin la columna exam_data (muy larga)
    df_csv = df.drop(columns=['exam_data'])
    output_file = f"{output_dir}/exams.csv"
    df_csv.to_csv(output_file, index=False)
    print(f"✓ Exámenes exportados: {len(df)} registros → {output_file}")

    # Guardar JSON completo con exam_data
    output_json = f"{output_dir}/exams_full.json"
    df.to_json(output_json, orient='records', indent=2, date_format='iso')
    print(f"✓ Exámenes completos (JSON) → {output_json}")

    return df

def export_exam_responses(conn, output_dir, user_id=None, exam_id=None):
    """Exportar respuestas de exámenes con sentimiento"""
    query = """
    SELECT
        er.id, er.exam_id, er.user_id, u.username,
        e.title as exam_title,
        er.question_number, er.student_answer,
        er.bloom_level, er.solo_level,
        er.evaluation_data,
        er.sentiment_score, er.sentiment_label,
        er.created_at
    FROM exam_responses er
    LEFT JOIN users u ON er.user_id = u.id
    LEFT JOIN exams e ON er.exam_id = e.id
    WHERE 1=1
    """

    if user_id:
        query += f" AND er.user_id = {user_id}"
    if exam_id:
        query += f" AND er.exam_id = {exam_id}"

    query += " ORDER BY er.exam_id, er.question_number"

    df = pd.read_sql_query(query, conn)
    output_file = f"{output_dir}/exam_responses.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Respuestas de exámenes exportadas: {len(df)} registros → {output_file}")

    # JSON con datos completos
    output_json = f"{output_dir}/exam_responses.json"
    df.to_json(output_json, orient='records', indent=2, date_format='iso')
    print(f"✓ Respuestas JSON → {output_json}")

    return df

def export_exam_results(conn, output_dir, user_id=None):
    """Exportar resultados finales de exámenes"""
    query = """
    SELECT
        r.id, r.exam_id, r.user_id, u.username,
        e.title as exam_title,
        r.predominant_solo_level, r.overall_description,
        r.strengths, r.improvement_plan,
        r.bloom_distribution, r.solo_distribution,
        r.created_at
    FROM exam_results r
    LEFT JOIN users u ON r.user_id = u.id
    LEFT JOIN exams e ON r.exam_id = e.id
    WHERE 1=1
    """

    if user_id:
        query += f" AND r.user_id = {user_id}"

    query += " ORDER BY r.created_at DESC"

    df = pd.read_sql_query(query, conn)
    output_file = f"{output_dir}/exam_results.json"
    df.to_json(output_file, orient='records', indent=2, date_format='iso')
    print(f"✓ Resultados de exámenes exportados: {len(df)} registros → {output_file}")

    return df

def export_student_progress(conn, output_dir, user_id=None):
    """Exportar progreso de estudiantes"""
    query = """
    SELECT
        sp.id, sp.user_id, u.username,
        sp.total_queries, sp.total_sessions, sp.avg_session_duration,
        sp.positive_feedback_count, sp.negative_feedback_count,
        sp.satisfaction_rate,
        sp.topics_explored, sp.complexity_distribution,
        sp.avg_sentiment,
        sp.bloom_distribution, sp.solo_distribution,
        sp.first_query_date, sp.last_query_date,
        sp.updated_at
    FROM student_progress sp
    LEFT JOIN users u ON sp.user_id = u.id
    WHERE 1=1
    """

    if user_id:
        query += f" AND sp.user_id = {user_id}"

    df = pd.read_sql_query(query, conn)
    output_file = f"{output_dir}/student_progress.json"
    df.to_json(output_file, orient='records', indent=2, date_format='iso')
    print(f"✓ Progreso de estudiantes exportado: {len(df)} registros → {output_file}")

    return df

def export_sentiment_analysis_summary(conn, output_dir):
    """Generar resumen de análisis de sentimiento"""

    # Análisis de mensajes
    query_messages = """
    SELECT
        u.username,
        COUNT(m.id) as total_messages,
        AVG(m.sentiment_score) as avg_sentiment,
        SUM(CASE WHEN m.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
        SUM(CASE WHEN m.sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
        SUM(CASE WHEN m.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
        m.query_complexity,
        m.bloom_level,
        m.solo_level
    FROM messages m
    LEFT JOIN conversations c ON m.conversation_id = c.id
    LEFT JOIN users u ON c.user_id = u.id
    WHERE m.role = 'user' AND m.sentiment_score IS NOT NULL
    GROUP BY u.username, m.query_complexity, m.bloom_level, m.solo_level
    """

    df_messages = pd.read_sql_query(query_messages, conn)
    output_file = f"{output_dir}/sentiment_summary_messages.csv"
    df_messages.to_csv(output_file, index=False)
    print(f"✓ Resumen de sentimiento (mensajes) → {output_file}")

    # Análisis de respuestas de examen
    query_exams = """
    SELECT
        u.username,
        e.title as exam_title,
        COUNT(er.id) as total_responses,
        AVG(er.sentiment_score) as avg_sentiment,
        SUM(CASE WHEN er.sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
        SUM(CASE WHEN er.sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
        SUM(CASE WHEN er.sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
        er.bloom_level,
        er.solo_level
    FROM exam_responses er
    LEFT JOIN users u ON er.user_id = u.id
    LEFT JOIN exams e ON er.exam_id = e.id
    WHERE er.sentiment_score IS NOT NULL
    GROUP BY u.username, e.title, er.bloom_level, er.solo_level
    """

    df_exams = pd.read_sql_query(query_exams, conn)
    output_file = f"{output_dir}/sentiment_summary_exams.csv"
    df_exams.to_csv(output_file, index=False)
    print(f"✓ Resumen de sentimiento (exámenes) → {output_file}")

    return df_messages, df_exams

def generate_export_report(output_dir, stats):
    """Generar reporte de exportación"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_file = f"{output_dir}/export_report.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("REPORTE DE EXPORTACIÓN - BASE DE DATOS RAG v2\n")
        f.write("="*60 + "\n")
        f.write(f"Fecha de exportación: {timestamp}\n")
        f.write(f"Base de datos: {DB_PATH}\n")
        f.write(f"Directorio de salida: {output_dir}\n\n")

        f.write("Estadísticas de exportación:\n")
        f.write("-"*60 + "\n")
        for key, value in stats.items():
            f.write(f"  {key}: {value}\n")

        f.write("\n" + "="*60 + "\n")

    print(f"\n✓ Reporte generado → {report_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Exportar datos de la base de datos RAG v2 para análisis de sentimiento'
    )
    parser.add_argument(
        '--user-id',
        type=int,
        help='Filtrar por ID de usuario específico'
    )
    parser.add_argument(
        '--conversation-id',
        type=int,
        help='Filtrar por ID de conversación específica'
    )
    parser.add_argument(
        '--exam-id',
        type=int,
        help='Filtrar por ID de examen específico'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=EXPORT_DIR,
        help=f'Directorio de salida (default: {EXPORT_DIR})'
    )

    args = parser.parse_args()

    # Configurar directorio de exportación
    output_dir = setup_export_directory() if args.output_dir == EXPORT_DIR else args.output_dir
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Crear subdirectorio con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_subdir = f"{output_dir}/export_{timestamp}"
    Path(export_subdir).mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print("EXPORTACIÓN DE BASE DE DATOS RAG v2")
    print("="*60 + "\n")

    # Conectar a la base de datos
    conn = get_connection()

    stats = {}

    try:
        # Exportar todas las tablas
        df_users = export_users(conn, export_subdir)
        stats['Usuarios'] = len(df_users)

        df_conversations = export_conversations(conn, export_subdir, args.user_id)
        stats['Conversaciones'] = len(df_conversations)

        df_messages = export_messages_with_sentiment(conn, export_subdir, args.user_id, args.conversation_id)
        stats['Mensajes'] = len(df_messages)

        df_exams = export_exams(conn, export_subdir, args.user_id)
        stats['Exámenes'] = len(df_exams)

        df_responses = export_exam_responses(conn, export_subdir, args.user_id, args.exam_id)
        stats['Respuestas de examen'] = len(df_responses)

        df_results = export_exam_results(conn, export_subdir, args.user_id)
        stats['Resultados de examen'] = len(df_results)

        df_progress = export_student_progress(conn, export_subdir, args.user_id)
        stats['Registros de progreso'] = len(df_progress)

        # Generar resúmenes de sentimiento
        print("\nGenerando resúmenes de análisis de sentimiento...")
        export_sentiment_analysis_summary(conn, export_subdir)

        # Generar reporte
        generate_export_report(export_subdir, stats)

        print("\n" + "="*60)
        print("✓ EXPORTACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"\nArchivos exportados en: {export_subdir}")
        print("\nArchivos generados:")
        for file in sorted(Path(export_subdir).glob("*")):
            size = file.stat().st_size / 1024
            print(f"  - {file.name} ({size:.1f} KB)")

    except Exception as e:
        print(f"\n✗ Error durante la exportación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
