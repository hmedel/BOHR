#!/usr/bin/env python3
"""
Script de ejemplo para análisis de sentimiento de datos exportados
Genera visualizaciones y estadísticas descriptivas
"""

import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

# Configurar estilo de gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def load_latest_export():
    """Cargar la exportación más reciente"""
    exports_dir = Path("./exports")
    if not exports_dir.exists():
        print("Error: No se encontró el directorio de exportaciones")
        sys.exit(1)

    # Buscar el directorio de exportación más reciente
    export_dirs = sorted(exports_dir.glob("export_*"), reverse=True)
    if not export_dirs:
        print("Error: No se encontraron exportaciones. Ejecuta export_db.py primero.")
        sys.exit(1)

    latest = export_dirs[0]
    print(f"Cargando exportación: {latest.name}\n")
    return latest

def analyze_message_sentiment(export_dir):
    """Análisis de sentimiento en mensajes"""
    print("="*60)
    print("ANÁLISIS DE SENTIMIENTO - MENSAJES")
    print("="*60 + "\n")

    messages_file = export_dir / "messages_sentiment.csv"
    if not messages_file.exists():
        print("No se encontró archivo de mensajes")
        return

    df = pd.read_csv(messages_file)

    # Filtrar solo mensajes de usuario con sentimiento
    df_user = df[(df['role'] == 'user') & (df['sentiment_score'].notna())]

    print(f"Total de mensajes analizados: {len(df_user)}\n")

    # Estadísticas generales
    print("Estadísticas de Sentimiento:")
    print("-" * 60)
    print(f"Sentimiento promedio: {df_user['sentiment_score'].mean():.3f}")
    print(f"Desviación estándar: {df_user['sentiment_score'].std():.3f}")
    print(f"Mínimo: {df_user['sentiment_score'].min():.3f}")
    print(f"Máximo: {df_user['sentiment_score'].max():.3f}")
    print()

    # Distribución por etiqueta
    print("Distribución por Etiqueta:")
    print("-" * 60)
    sentiment_dist = df_user['sentiment_label'].value_counts()
    for label, count in sentiment_dist.items():
        pct = (count / len(df_user)) * 100
        print(f"  {label:10s}: {count:4d} ({pct:5.1f}%)")
    print()

    # Por complejidad
    print("Sentimiento Promedio por Complejidad:")
    print("-" * 60)
    complexity_sentiment = df_user.groupby('query_complexity')['sentiment_score'].agg(['mean', 'count'])
    print(complexity_sentiment)
    print()

    # Por usuario
    print("Top 10 Usuarios por Actividad:")
    print("-" * 60)
    user_stats = df_user.groupby('username').agg({
        'sentiment_score': 'mean',
        'id': 'count'
    }).rename(columns={'id': 'num_messages'}).sort_values('num_messages', ascending=False).head(10)
    print(user_stats)
    print()

    # Generar gráficos
    generate_message_plots(df_user, export_dir)

    return df_user

def analyze_exam_sentiment(export_dir):
    """Análisis de sentimiento en respuestas de examen"""
    print("\n" + "="*60)
    print("ANÁLISIS DE SENTIMIENTO - RESPUESTAS DE EXAMEN")
    print("="*60 + "\n")

    responses_file = export_dir / "exam_responses.csv"
    if not responses_file.exists():
        print("No se encontró archivo de respuestas de examen")
        return

    df = pd.read_csv(responses_file)
    df_sentiment = df[df['sentiment_score'].notna()]

    print(f"Total de respuestas analizadas: {len(df_sentiment)}\n")

    if len(df_sentiment) == 0:
        print("No hay datos de sentimiento en respuestas de examen")
        return

    # Estadísticas generales
    print("Estadísticas de Sentimiento:")
    print("-" * 60)
    print(f"Sentimiento promedio: {df_sentiment['sentiment_score'].mean():.3f}")
    print(f"Desviación estándar: {df_sentiment['sentiment_score'].std():.3f}")
    print()

    # Por nivel de Bloom
    print("Sentimiento por Nivel de Bloom:")
    print("-" * 60)
    bloom_sentiment = df_sentiment.groupby('bloom_level')['sentiment_score'].agg(['mean', 'count'])
    print(bloom_sentiment)
    print()

    # Por nivel SOLO
    print("Sentimiento por Nivel SOLO:")
    print("-" * 60)
    solo_sentiment = df_sentiment.groupby('solo_level')['sentiment_score'].agg(['mean', 'count'])
    print(solo_sentiment)
    print()

    # Distribución de niveles
    print("Distribución de Niveles Cognitivos (Bloom):")
    print("-" * 60)
    bloom_dist = df['bloom_level'].value_counts()
    for level, count in bloom_dist.items():
        pct = (count / len(df)) * 100
        print(f"  {level:15s}: {count:3d} ({pct:5.1f}%)")
    print()

    print("Distribución de Niveles de Comprensión (SOLO):")
    print("-" * 60)
    solo_dist = df['solo_level'].value_counts()
    for level, count in solo_dist.items():
        pct = (count / len(df)) * 100
        print(f"  {level:15s}: {count:3d} ({pct:5.1f}%)")
    print()

    # Generar gráficos
    generate_exam_plots(df_sentiment, df, export_dir)

    return df_sentiment

def generate_message_plots(df, export_dir):
    """Generar visualizaciones para mensajes"""
    output_dir = export_dir / "analysis_plots"
    output_dir.mkdir(exist_ok=True)

    # 1. Distribución de sentimiento
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Histograma de scores
    axes[0, 0].hist(df['sentiment_score'].dropna(), bins=20, color='skyblue', edgecolor='black')
    axes[0, 0].set_xlabel('Sentiment Score')
    axes[0, 0].set_ylabel('Frecuencia')
    axes[0, 0].set_title('Distribución de Sentiment Scores')
    axes[0, 0].axvline(0, color='red', linestyle='--', alpha=0.5)

    # Por etiqueta
    sentiment_counts = df['sentiment_label'].value_counts()
    axes[0, 1].bar(sentiment_counts.index, sentiment_counts.values, color=['green', 'gray', 'red'])
    axes[0, 1].set_xlabel('Sentiment Label')
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].set_title('Distribución por Etiqueta')

    # Por complejidad
    complexity_data = df.groupby('query_complexity')['sentiment_score'].mean()
    axes[1, 0].bar(complexity_data.index, complexity_data.values, color='coral')
    axes[1, 0].set_xlabel('Query Complexity')
    axes[1, 0].set_ylabel('Average Sentiment')
    axes[1, 0].set_title('Sentimiento Promedio por Complejidad')
    axes[1, 0].axhline(0, color='red', linestyle='--', alpha=0.5)

    # Serie temporal (si hay datos suficientes)
    if 'created_at' in df.columns:
        df_temp = df.copy()
        df_temp['created_at'] = pd.to_datetime(df_temp['created_at'])
        df_temp = df_temp.sort_values('created_at')
        if len(df_temp) > 5:
            df_temp['rolling_sentiment'] = df_temp['sentiment_score'].rolling(window=5, min_periods=1).mean()
            axes[1, 1].plot(df_temp['created_at'], df_temp['rolling_sentiment'], color='purple', linewidth=2)
            axes[1, 1].set_xlabel('Fecha')
            axes[1, 1].set_ylabel('Sentiment (promedio móvil)')
            axes[1, 1].set_title('Evolución Temporal del Sentimiento')
            axes[1, 1].tick_params(axis='x', rotation=45)
            axes[1, 1].axhline(0, color='red', linestyle='--', alpha=0.5)
        else:
            axes[1, 1].text(0.5, 0.5, 'Datos insuficientes\npara serie temporal',
                           ha='center', va='center', transform=axes[1, 1].transAxes)

    plt.tight_layout()
    output_file = output_dir / "messages_sentiment_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico generado: {output_file}")
    plt.close()

def generate_exam_plots(df_sentiment, df_all, export_dir):
    """Generar visualizaciones para exámenes"""
    output_dir = export_dir / "analysis_plots"
    output_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Sentimiento por Bloom
    bloom_data = df_all.groupby('bloom_level')['sentiment_score'].mean().sort_values()
    axes[0, 0].barh(bloom_data.index, bloom_data.values, color='lightblue')
    axes[0, 0].set_xlabel('Average Sentiment')
    axes[0, 0].set_title('Sentimiento por Nivel de Bloom')
    axes[0, 0].axvline(0, color='red', linestyle='--', alpha=0.5)

    # Distribución de Bloom
    bloom_dist = df_all['bloom_level'].value_counts()
    axes[0, 1].pie(bloom_dist.values, labels=bloom_dist.index, autopct='%1.1f%%', startangle=90)
    axes[0, 1].set_title('Distribución de Niveles Bloom')

    # Sentimiento por SOLO
    solo_data = df_all.groupby('solo_level')['sentiment_score'].mean().sort_values()
    axes[1, 0].barh(solo_data.index, solo_data.values, color='lightcoral')
    axes[1, 0].set_xlabel('Average Sentiment')
    axes[1, 0].set_title('Sentimiento por Nivel SOLO')
    axes[1, 0].axvline(0, color='red', linestyle='--', alpha=0.5)

    # Distribución de SOLO
    solo_dist = df_all['solo_level'].value_counts()
    axes[1, 1].pie(solo_dist.values, labels=solo_dist.index, autopct='%1.1f%%', startangle=90)
    axes[1, 1].set_title('Distribución de Niveles SOLO')

    plt.tight_layout()
    output_file = output_dir / "exams_sentiment_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico generado: {output_file}")
    plt.close()

def analyze_student_progress(export_dir):
    """Analizar progreso de estudiantes"""
    print("\n" + "="*60)
    print("ANÁLISIS DE PROGRESO DE ESTUDIANTES")
    print("="*60 + "\n")

    progress_file = export_dir / "student_progress.json"
    if not progress_file.exists():
        print("No se encontró archivo de progreso")
        return

    df = pd.read_json(progress_file)

    print(f"Total de estudiantes con progreso registrado: {len(df)}\n")

    print("Estadísticas de Engagement:")
    print("-" * 60)
    print(f"Promedio de consultas por estudiante: {df['total_queries'].mean():.1f}")
    print(f"Promedio de sesiones por estudiante: {df['total_sessions'].mean():.1f}")
    print(f"Tasa de satisfacción promedio: {df['satisfaction_rate'].mean():.2%}")
    print(f"Sentimiento promedio: {df['avg_sentiment'].mean():.3f}")
    print()

    # Top estudiantes por actividad
    print("Top 10 Estudiantes por Actividad:")
    print("-" * 60)
    top_students = df.nlargest(10, 'total_queries')[['username', 'total_queries', 'total_sessions', 'satisfaction_rate', 'avg_sentiment']]
    print(top_students.to_string(index=False))
    print()

    return df

def generate_summary_report(export_dir, df_messages, df_exams, df_progress):
    """Generar reporte resumen en texto"""
    output_file = export_dir / "sentiment_analysis_summary.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("REPORTE DE ANÁLISIS DE SENTIMIENTO - SISTEMA RAG v2\n")
        f.write("="*70 + "\n\n")

        f.write(f"Fecha de análisis: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Exportación analizada: {export_dir.name}\n\n")

        # Resumen ejecutivo
        f.write("RESUMEN EJECUTIVO\n")
        f.write("-"*70 + "\n")

        if df_messages is not None:
            f.write(f"Total de mensajes analizados: {len(df_messages)}\n")
            f.write(f"Sentimiento promedio (mensajes): {df_messages['sentiment_score'].mean():.3f}\n")
            sentiment_dist = df_messages['sentiment_label'].value_counts(normalize=True)
            f.write(f"  - Positivo: {sentiment_dist.get('positive', 0):.1%}\n")
            f.write(f"  - Neutral: {sentiment_dist.get('neutral', 0):.1%}\n")
            f.write(f"  - Negativo: {sentiment_dist.get('negative', 0):.1%}\n")
            f.write("\n")

        if df_exams is not None and len(df_exams) > 0:
            f.write(f"Total de respuestas de examen: {len(df_exams)}\n")
            f.write(f"Sentimiento promedio (exámenes): {df_exams['sentiment_score'].mean():.3f}\n")
            f.write("\n")

        if df_progress is not None:
            f.write(f"Estudiantes con progreso registrado: {len(df_progress)}\n")
            f.write(f"Tasa de satisfacción promedio: {df_progress['satisfaction_rate'].mean():.2%}\n")
            f.write("\n")

        # Recomendaciones
        f.write("\nRECOMENDACIONES\n")
        f.write("-"*70 + "\n")

        if df_messages is not None:
            avg_sentiment = df_messages['sentiment_score'].mean()
            if avg_sentiment < -0.2:
                f.write("⚠ ALERTA: Sentimiento general negativo en mensajes.\n")
                f.write("  Considerar revisar la experiencia del usuario.\n\n")
            elif avg_sentiment > 0.2:
                f.write("✓ Sentimiento general positivo en mensajes.\n\n")
            else:
                f.write("• Sentimiento neutral. Monitorear tendencias.\n\n")

            # Complejidad
            complexity_sentiment = df_messages.groupby('query_complexity')['sentiment_score'].mean()
            if 'advanced' in complexity_sentiment.index and complexity_sentiment['advanced'] < -0.1:
                f.write("⚠ Las consultas avanzadas muestran sentimiento negativo.\n")
                f.write("  Mejorar soporte para temas complejos.\n\n")

        f.write("\n" + "="*70 + "\n")

    print(f"\n✓ Reporte resumen generado: {output_file}")

def main():
    print("\n" + "="*60)
    print("ANÁLISIS DE SENTIMIENTO - BASE DE DATOS RAG v2")
    print("="*60 + "\n")

    # Cargar exportación más reciente
    export_dir = load_latest_export()

    # Realizar análisis
    df_messages = analyze_message_sentiment(export_dir)
    df_exams = analyze_exam_sentiment(export_dir)
    df_progress = analyze_student_progress(export_dir)

    # Generar reporte resumen
    generate_summary_report(export_dir, df_messages, df_exams, df_progress)

    print("\n" + "="*60)
    print("✓ ANÁLISIS COMPLETADO")
    print("="*60)
    print(f"\nResultados guardados en: {export_dir}/analysis_plots/")
    print("\nGráficos generados:")
    plots_dir = export_dir / "analysis_plots"
    if plots_dir.exists():
        for plot_file in sorted(plots_dir.glob("*.png")):
            print(f"  - {plot_file.name}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAnálisis interrumpido por el usuario")
    except Exception as e:
        print(f"\n✗ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
