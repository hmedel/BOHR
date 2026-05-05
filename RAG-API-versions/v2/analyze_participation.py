#!/usr/bin/env python3
"""
Genera un reporte HTML de participación de usuarios del sistema BOHR RAG v2.

Uso:
    conda activate bohrenv
    python analyze_participation.py

Salida:
    analytics/reports/reporte_YYYYMMDD_HHMMSS.html
    analytics/snapshots/snapshot_YYYYMMDD_HHMMSS/  (CSVs del análisis)
"""

import os
import sys
import shutil
import sqlite3
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "data" / "rag_system.db"
RUN_TS   = datetime.now().strftime("%Y%m%d_%H%M%S")
SNAPSHOT_DIR = BASE_DIR / "analytics" / "snapshots" / f"snapshot_{RUN_TS}"
REPORT_PATH  = BASE_DIR / "analytics" / "reports"  / f"reporte_{RUN_TS}.html"

SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Carga de datos ─────────────────────────────────────────────────────────────
def load_data():
    con = sqlite3.connect(DB_PATH)

    users = pd.read_sql_query("""
        SELECT id, full_name, email, is_admin, created_at FROM users
    """, con)

    messages = pd.read_sql_query("""
        SELECT m.id, m.conversation_id, m.role, m.content,
               m.sentiment_score, m.sentiment_label,
               m.query_complexity, m.topics, m.bloom_level, m.solo_level,
               m.response_time, m.feedback, m.created_at,
               c.user_id
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
    """, con)

    conversations = pd.read_sql_query("""
        SELECT id, user_id, title, created_at FROM conversations
    """, con)

    exams = pd.read_sql_query("""
        SELECT e.id, e.user_id, e.title, e.status, e.total_questions,
               e.topics_covered, e.created_at
        FROM exams e
    """, con)

    exam_responses = pd.read_sql_query("""
        SELECT er.id, er.exam_id, er.user_id, er.question_number,
               er.bloom_level, er.solo_level, er.sentiment_score, er.sentiment_label
        FROM exam_responses er
    """, con)

    exam_results = pd.read_sql_query("""
        SELECT res.exam_id, res.user_id, res.predominant_solo_level,
               res.strengths, res.improvement_plan
        FROM exam_results res
    """, con)

    progress = pd.read_sql_query("""
        SELECT sp.user_id, sp.total_queries, sp.topics_explored,
               sp.complexity_distribution, sp.first_query_date, sp.last_query_date
        FROM student_progress sp
    """, con)

    query_logs = pd.read_sql_query("""
        SELECT id, user_id, query, sources_found, top_k_used, response_time, created_at
        FROM query_logs
    """, con)

    con.close()
    return users, messages, conversations, exams, exam_responses, exam_results, progress, query_logs


# ── Cómputo de métricas ────────────────────────────────────────────────────────
def compute_metrics(users, messages, conversations, exams, exam_responses, progress, query_logs):
    user_msgs = messages[messages["role"] == "user"].copy()

    # Participación por usuario
    by_user = (
        user_msgs.groupby("user_id")
        .agg(
            preguntas=("id", "count"),
            conversaciones=("conversation_id", "nunique"),
            tiempo_prom=("response_time", "mean"),
            ultima_actividad=("created_at", "max"),
        )
        .reset_index()
    )
    exams_count = exams.groupby("user_id").size().reset_index(name="examenes")
    by_user = by_user.merge(exams_count, on="user_id", how="left").fillna({"examenes": 0})
    by_user = by_user.merge(users[["id", "full_name", "email", "is_admin"]], left_on="user_id", right_on="id")
    by_user["examenes"] = by_user["examenes"].astype(int)
    by_user["tiempo_prom"] = by_user["tiempo_prom"].round(1)

    # Todos los usuarios (incluye inactivos)
    all_users = users.merge(by_user[["user_id", "preguntas", "conversaciones", "examenes",
                                      "tiempo_prom", "ultima_actividad"]],
                             left_on="id", right_on="user_id", how="left").fillna(0)
    all_users["activo"] = all_users["preguntas"] > 0

    # Complejidad
    complexity = (
        user_msgs[user_msgs["query_complexity"].notna()]
        .groupby(["user_id", "query_complexity"])
        .size()
        .reset_index(name="count")
        .merge(users[["id", "full_name"]], left_on="user_id", right_on="id")
    )

    # Actividad diaria
    user_msgs["date"] = pd.to_datetime(user_msgs["created_at"]).dt.date
    daily = user_msgs.groupby("date").agg(consultas=("id", "count")).reset_index()

    # Tiempos de respuesta por día
    daily_time = query_logs.copy()
    daily_time["date"] = pd.to_datetime(daily_time["created_at"]).dt.date
    daily_time = daily_time.groupby("date").agg(
        consultas=("id", "count"),
        tiempo_prom=("response_time", "mean"),
        tiempo_max=("response_time", "max"),
    ).reset_index()
    daily_time["tiempo_prom"] = daily_time["tiempo_prom"].round(1)
    daily_time["tiempo_max"] = daily_time["tiempo_max"].round(1)

    return all_users, by_user, complexity, daily, daily_time


# ── Gráficas ───────────────────────────────────────────────────────────────────
def make_charts(all_users, by_user, complexity, daily, daily_time, exam_responses):
    charts = {}

    # 1. Participación total
    active_df = by_user[by_user["is_admin"] == 0].sort_values("preguntas", ascending=True)
    fig = go.Figure(go.Bar(
        x=active_df["preguntas"],
        y=active_df["full_name"],
        orientation="h",
        marker_color="#4C72B0",
        text=active_df["preguntas"],
        textposition="outside",
    ))
    fig.update_layout(title="Preguntas realizadas por estudiante",
                      xaxis_title="Número de preguntas", height=max(300, len(active_df) * 35 + 80),
                      margin=dict(l=10, r=30, t=40, b=40))
    charts["bar_preguntas"] = fig.to_html(full_html=False, include_plotlyjs=False)

    # 2. Activos vs inactivos (excluyendo admin)
    no_admin = all_users[all_users["is_admin"] == 0]
    counts = no_admin["activo"].value_counts()
    fig2 = go.Figure(go.Pie(
        labels=["Con actividad", "Sin actividad"],
        values=[counts.get(True, 0), counts.get(False, 0)],
        hole=0.45,
        marker_colors=["#2ca02c", "#d62728"],
    ))
    fig2.update_layout(title="Adopción del sistema (estudiantes)", margin=dict(t=40, b=20))
    charts["pie_adopcion"] = fig2.to_html(full_html=False, include_plotlyjs=False)

    # 3. Distribución de complejidad
    if not complexity.empty:
        no_admin_ids = all_users[all_users["is_admin"] == 0]["id"].tolist()
        cplx = complexity[complexity["user_id"].isin(no_admin_ids)]
        order = ["basic", "intermediate", "advanced"]
        cplx_grp = cplx.groupby("query_complexity")["count"].sum().reindex(order).fillna(0)
        fig3 = go.Figure(go.Bar(
            x=cplx_grp.index,
            y=cplx_grp.values,
            marker_color=["#aec7e8", "#4C72B0", "#1f4e8c"],
            text=cplx_grp.values.astype(int),
            textposition="outside",
        ))
        fig3.update_layout(title="Distribución de complejidad de consultas (estudiantes)",
                           xaxis_title="Nivel", yaxis_title="Cantidad",
                           margin=dict(t=40, b=40))
        charts["bar_complejidad"] = fig3.to_html(full_html=False, include_plotlyjs=False)

    # 4. Actividad diaria
    fig4 = go.Figure(go.Scatter(
        x=daily["date"].astype(str),
        y=daily["consultas"],
        mode="lines+markers",
        line=dict(color="#4C72B0", width=2),
        marker=dict(size=6),
        fill="tozeroy",
        fillcolor="rgba(76,114,176,0.15)",
    ))
    fig4.update_layout(title="Consultas por día",
                       xaxis_title="Fecha", yaxis_title="Consultas",
                       margin=dict(t=40, b=40))
    charts["line_actividad"] = fig4.to_html(full_html=False, include_plotlyjs=False)

    # 5. Tiempo de respuesta promedio por día
    fig5 = make_subplots(specs=[[{"secondary_y": True}]])
    fig5.add_trace(go.Bar(
        x=daily_time["date"].astype(str),
        y=daily_time["consultas"],
        name="Consultas",
        marker_color="rgba(76,114,176,0.4)",
    ), secondary_y=False)
    fig5.add_trace(go.Scatter(
        x=daily_time["date"].astype(str),
        y=daily_time["tiempo_prom"],
        name="Tiempo prom (s)",
        line=dict(color="#d62728", width=2),
        mode="lines+markers",
    ), secondary_y=True)
    fig5.update_layout(title="Consultas y tiempo de respuesta por día",
                       margin=dict(t=40, b=40))
    fig5.update_yaxes(title_text="Consultas", secondary_y=False)
    fig5.update_yaxes(title_text="Segundos", secondary_y=True)
    charts["bar_tiempos"] = fig5.to_html(full_html=False, include_plotlyjs=False)

    # 6. SOLO levels en exámenes
    if not exam_responses.empty:
        solo_counts = exam_responses["solo_level"].value_counts()
        fig6 = go.Figure(go.Bar(
            x=solo_counts.index,
            y=solo_counts.values,
            marker_color="#9467bd",
            text=solo_counts.values,
            textposition="outside",
        ))
        fig6.update_layout(title="Niveles SOLO en respuestas de examen",
                           xaxis_title="Nivel SOLO", yaxis_title="Frecuencia",
                           margin=dict(t=40, b=40))
        charts["bar_solo"] = fig6.to_html(full_html=False, include_plotlyjs=False)

    return charts


# ── Snapshots CSV ──────────────────────────────────────────────────────────────
def save_snapshot(all_users, messages, exams, exam_responses, exam_results, query_logs):
    all_users.to_csv(SNAPSHOT_DIR / "usuarios.csv", index=False)
    messages.to_csv(SNAPSHOT_DIR / "mensajes.csv", index=False)
    exams.to_csv(SNAPSHOT_DIR / "examenes.csv", index=False)
    exam_responses.to_csv(SNAPSHOT_DIR / "exam_responses.csv", index=False)
    exam_results.to_csv(SNAPSHOT_DIR / "exam_results.csv", index=False)
    query_logs.to_csv(SNAPSHOT_DIR / "query_logs.csv", index=False)
    print(f"  Snapshot guardado en: {SNAPSHOT_DIR}")


# ── HTML ───────────────────────────────────────────────────────────────────────
def build_html(all_users, by_user, daily_time, charts, exam_results):
    # KPIs
    no_admin = all_users[all_users["is_admin"] == 0]
    total_est  = len(no_admin)
    activos    = int(no_admin["activo"].sum())
    inactivos  = total_est - activos
    total_preg = int(no_admin["preguntas"].sum())
    total_exam = int(no_admin["examenes"].sum())
    avg_time   = round(daily_time["tiempo_prom"].mean(), 1) if not daily_time.empty else 0

    # Tabla de usuarios activos
    tabla_rows = ""
    active_students = by_user[by_user["is_admin"] == 0].sort_values("preguntas", ascending=False)
    for _, row in active_students.iterrows():
        ultima = str(row["ultima_actividad"])[:10] if row["ultima_actividad"] else "—"
        tabla_rows += f"""
        <tr>
          <td>{row['full_name']}</td>
          <td>{row['email']}</td>
          <td class="num">{int(row['preguntas'])}</td>
          <td class="num">{int(row['conversaciones'])}</td>
          <td class="num">{int(row['examenes'])}</td>
          <td class="num">{row['tiempo_prom']}s</td>
          <td>{ultima}</td>
        </tr>"""

    # Tabla inactivos
    inactivos_rows = ""
    for _, row in no_admin[~no_admin["activo"]].iterrows():
        inactivos_rows += f"<tr><td>{row['full_name']}</td><td>{row['email']}</td></tr>"

    # Exámenes
    exam_rows = ""
    for _, row in exam_results.iterrows():
        strengths = json.loads(row["strengths"]) if isinstance(row["strengths"], str) else []
        plan_raw  = row["improvement_plan"]
        try:
            plan = json.loads(plan_raw).get("plan", plan_raw) if isinstance(plan_raw, str) else ""
        except Exception:
            plan = str(plan_raw)
        exam_rows += f"""
        <tr>
          <td>{row['user_id']}</td>
          <td>{row['predominant_solo_level']}</td>
          <td>{', '.join(strengths) if strengths else '—'}</td>
          <td>{plan}</td>
        </tr>"""

    chart = lambda k: charts.get(k, "<p style='color:#999'>Sin datos suficientes</p>")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reporte de Participación BOHR RAG v2 — {RUN_TS[:8]}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  :root {{
    --primary: #4C72B0;
    --bg: #f7f8fa;
    --card: #ffffff;
    --border: #e0e4ec;
    --text: #222;
    --muted: #666;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); font-size: 14px; }}
  header {{ background: var(--primary); color: #fff; padding: 20px 32px; }}
  header h1 {{ font-size: 1.4rem; font-weight: 600; }}
  header p {{ opacity: .8; margin-top: 4px; font-size: .85rem; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px 16px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; text-align: center; }}
  .kpi .val {{ font-size: 2rem; font-weight: 700; color: var(--primary); }}
  .kpi .lbl {{ color: var(--muted); font-size: .8rem; margin-top: 4px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; }}
  .card h2 {{ font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: var(--primary); border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
  th {{ background: #f0f3fa; text-align: left; padding: 8px 10px; font-weight: 600; color: var(--muted); border-bottom: 2px solid var(--border); }}
  td {{ padding: 7px 10px; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f5f7ff; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: .75rem; }}
  .badge.active {{ background: #d4edda; color: #155724; }}
  .badge.inactive {{ background: #f8d7da; color: #721c24; }}
  .section-full {{ margin-bottom: 20px; }}
  .ts {{ color: var(--muted); font-size: .75rem; text-align: right; margin-top: 24px; }}
  @media (max-width: 700px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>Reporte de Participación — BOHR RAG v2</h1>
  <p>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;·&nbsp; Base de datos: {DB_PATH.name}</p>
</header>
<div class="container">

  <!-- KPIs -->
  <div class="kpis">
    <div class="kpi"><div class="val">{total_est}</div><div class="lbl">Estudiantes registrados</div></div>
    <div class="kpi"><div class="val">{activos}</div><div class="lbl">Con actividad</div></div>
    <div class="kpi"><div class="val">{inactivos}</div><div class="lbl">Sin actividad</div></div>
    <div class="kpi"><div class="val">{total_preg}</div><div class="lbl">Consultas totales</div></div>
    <div class="kpi"><div class="val">{total_exam}</div><div class="lbl">Exámenes tomados</div></div>
    <div class="kpi"><div class="val">{avg_time}s</div><div class="lbl">Tiempo prom. respuesta</div></div>
  </div>

  <!-- Gráfica principal + pie -->
  <div class="grid-2">
    <div class="card">{chart('bar_preguntas')}</div>
    <div class="card">{chart('pie_adopcion')}</div>
  </div>

  <!-- Actividad diaria -->
  <div class="section-full card" style="margin-bottom:20px">
    {chart('line_actividad')}
  </div>

  <!-- Tiempos + complejidad -->
  <div class="grid-2">
    <div class="card">{chart('bar_tiempos')}</div>
    <div class="card">{chart('bar_complejidad')}</div>
  </div>

  <!-- SOLO si hay exámenes -->
  {'<div class="section-full card" style="margin-bottom:20px">' + chart('bar_solo') + '</div>' if 'bar_solo' in charts else ''}

  <!-- Tabla estudiantes activos -->
  <div class="section-full card" style="margin-bottom:20px">
    <h2>Detalle por estudiante (con actividad)</h2>
    <table>
      <thead><tr>
        <th>Nombre</th><th>Email</th>
        <th>Preguntas</th><th>Conversaciones</th><th>Exámenes</th>
        <th>T.prom</th><th>Última actividad</th>
      </tr></thead>
      <tbody>{tabla_rows}</tbody>
    </table>
  </div>

  <!-- Tabla inactivos -->
  <div class="section-full card" style="margin-bottom:20px">
    <h2>Estudiantes sin actividad ({inactivos})</h2>
    <table>
      <thead><tr><th>Nombre</th><th>Email</th></tr></thead>
      <tbody>{inactivos_rows}</tbody>
    </table>
  </div>

  <!-- Resultados de exámenes -->
  {'<div class="section-full card" style="margin-bottom:20px"><h2>Resultados de exámenes</h2><table><thead><tr><th>User ID</th><th>Nivel SOLO predominante</th><th>Fortalezas</th><th>Plan de mejora</th></tr></thead><tbody>' + exam_rows + '</tbody></table></div>' if exam_rows else ''}

  <p class="ts">Snapshot guardado en: analytics/snapshots/snapshot_{RUN_TS}/</p>
</div>
</body>
</html>"""
    return html


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if not DB_PATH.exists():
        print(f"ERROR: No se encontró la base de datos en {DB_PATH}")
        sys.exit(1)

    print(f"Analizando {DB_PATH} ...")
    users, messages, conversations, exams, exam_responses, exam_results, progress, query_logs = load_data()

    print(f"  {len(users)} usuarios, {len(messages)} mensajes, {len(exams)} exámenes")

    all_users, by_user, complexity, daily, daily_time = compute_metrics(
        users, messages, conversations, exams, exam_responses, progress, query_logs
    )

    print("  Generando gráficas ...")
    charts = make_charts(all_users, by_user, complexity, daily, daily_time, exam_responses)

    print("  Guardando snapshot CSV ...")
    save_snapshot(all_users, messages, exams, exam_responses, exam_results, query_logs)

    print("  Construyendo reporte HTML ...")
    html = build_html(all_users, by_user, daily_time, charts, exam_results)

    REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"\nReporte listo: {REPORT_PATH}")
    print(f"  Abrir con: xdg-open '{REPORT_PATH}'")


if __name__ == "__main__":
    main()
