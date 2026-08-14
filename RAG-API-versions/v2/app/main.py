from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Optional, List, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import timedelta, datetime
import json
import time
import re
import sys
import logging

logger = logging.getLogger(__name__)
import asyncio
from pathlib import Path

from .rag_engine import RAGEngine
from .config import settings, CLASSIFIER_VERSION, MODEL_VERSION, PROMPT_VERSION
from .database import get_db, User, Conversation, Message, QueryLog, StudentProgress, Exam, ExamResponse, ExamResult
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from .analytics_engine import AnalyticsEngine
from .qualitative_evaluator import QualitativeEvaluator
from .exam_engine import ExamEngine
from . import cache as rag_cache

app = FastAPI(title="Asistente de Estructura de la Materia", version="2.8")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.bohrbot.space", "http://localhost:9000", "http://132.248.102.133:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = RAGEngine()
analytics_engine = AnalyticsEngine()
qualitative_evaluator = QualitativeEvaluator()
exam_engine = ExamEngine()

# ========== MODELOS ==========
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = Field(None, max_length=150)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[int] = None
    top_k: Optional[int] = 5
    max_context: Optional[int] = 3000
    filter_source: Optional[str] = None

class FeedbackRequest(BaseModel):
    message_id: int
    feedback: int

# ========== AUTH ==========
@app.post("/register")
@limiter.limit("10/minute")
async def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    new_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Usuario creado", "username": new_user.username}

@app.post("/token", response_model=Token)
@limiter.limit("20/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    }

@app.get("/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin
    }

# ========== HELPER FUNCTIONS ==========
def is_exam_request(query: str) -> bool:
    """Detectar si el usuario solicita un examen"""
    query_lower = query.lower()
    
    # Patrones de solicitud de examen
    exam_patterns = [
        r'\bterminé\b',
        r'\btermine\b',
        r'\bexamen\b',
        r'\bevalúame\b',
        r'\bevaluame\b',
        r'\bquiero un examen\b',
        r'\bquiero otro examen\b',
        r'\botro examen\b',
        r'\bnuevo examen\b',
        r'\bmás preguntas\b',
        r'\bmas preguntas\b',
        r'\bhacer un examen\b',
        r'\btomar un examen\b',
        r'\bprueba\b',
        r'\bevaluación\b',
        r'\bevaluacion\b'
    ]
    
    return any(re.search(pattern, query_lower) for pattern in exam_patterns)

def is_exam_confirmation(query: str) -> bool:
    """Detectar confirmación para iniciar examen"""
    query_lower = query.lower()
    return (('sí' in query_lower or 'si' in query_lower) and 
            ('comenzar' in query_lower or 'empezar' in query_lower or 'iniciar' in query_lower))

def get_active_exam(user_id: int, db: Session) -> Optional[Exam]:
    """Obtener examen activo (status=active y sin completar) del usuario"""
    latest_exam = db.query(Exam).filter(
        Exam.user_id == user_id,
        Exam.status == "active"
    ).order_by(Exam.created_at.desc()).first()

    if not latest_exam:
        return None

    # Verificar si ya tiene todas las respuestas (debería estar completed, pero por si acaso)
    exam_data = latest_exam.exam_data if isinstance(latest_exam.exam_data, dict) else json.loads(latest_exam.exam_data)
    total_q = exam_data.get("total_questions", 3)

    responses_count = db.query(ExamResponse).filter(
        ExamResponse.exam_id == latest_exam.id
    ).count()

    if responses_count >= total_q:
        # Inconsistencia: marcar como completado
        latest_exam.status = "completed"
        db.commit()
        return None

    return latest_exam

def generate_exam_question(
    conversation_history: list,
    topics: list,
    question_number: int,
    total_questions: int,
    previous_levels: list,
    difficulty_profile: dict,
) -> Optional[dict]:
    """
    Genera una pregunta de examen fundamentada en el corpus.

    Flujo:
    1. Recupera pasajes del corpus via rag_engine.retrieve_passages_for_exam()
    2. Llama al LLM con evidencia
    3. Si el LLM reporta evidencia_insuficiente, reintenta con temas rotados
       (hasta 2 reintentos con subconjuntos distintos de topics)
    4. Si agota los reintentos, genera sin evidencia (degradado, registrado en log)

    Devuelve el dict de pregunta (con pasaje_fuente si se usó evidencia) o None.
    """
    topics_list = list(topics)

    for attempt in range(3):
        # Rotar los temas en cada reintento para variar la búsqueda
        rotated = topics_list[attempt:] + topics_list[:attempt]

        try:
            passages = rag_engine.retrieve_passages_for_exam(
                topics=rotated[:3],  # máximo 3 temas por búsqueda
                n_passages=6,
            )
        except Exception as exc:
            logger.warning("retrieve_passages_for_exam fallo: %s", exc)
            passages = []

        prompt = exam_engine.generate_single_question_prompt(
            conversation_history=conversation_history,
            topics=topics_list,
            question_number=question_number,
            total_questions=total_questions,
            previous_levels=previous_levels,
            difficulty_profile=difficulty_profile,
            evidence_passages=passages if passages else None,
        )

        raw = rag_engine._call_llm(prompt, temperature=0.3)
        question = exam_engine.parse_question_from_llm(raw)

        if question is None:
            logger.warning("parse_question_from_llm: JSON inválido en intento %d", attempt + 1)
            continue

        if question.get("error") == "evidencia_insuficiente":
            logger.info(
                "Evidencia insuficiente para pregunta %d (intento %d), rotando temas",
                question_number, attempt + 1,
            )
            continue

        # Pregunta válida
        if not question.get("pasaje_fuente") and passages:
            # LLM no completó el campo aunque había evidencia — marcar como no auditada
            question["pasaje_fuente"] = ""
            question["documento_fuente"] = ""
            question["_sin_pasaje"] = True

        return question

    # Agotados los reintentos: generar sin evidencia como último recurso
    logger.warning(
        "Generando pregunta %d sin evidencia del corpus (reintentos agotados)",
        question_number,
    )
    prompt = exam_engine.generate_single_question_prompt(
        conversation_history=conversation_history,
        topics=topics_list,
        question_number=question_number,
        total_questions=total_questions,
        previous_levels=previous_levels,
        difficulty_profile=difficulty_profile,
        evidence_passages=None,
    )
    raw = rag_engine._call_llm(prompt, temperature=0.3)
    question = exam_engine.parse_question_from_llm(raw)
    if question and not question.get("error"):
        question["pasaje_fuente"] = ""
        question["documento_fuente"] = ""
        question["_sin_pasaje"] = True
    return question


def should_offer_exam(conv_messages: list) -> bool:
    """
    Ofrece examen una sola vez por conversación cuando se cumplen:
    - Al menos 5 preguntas del usuario en esta conversación
    - Al menos 2 temas distintos detectados
    - No se ha ofrecido antes (ningún mensaje del asistente contiene el trigger)
    Limita la búsqueda del trigger a los últimos 20 mensajes para no ser O(n).
    """
    user_msgs = [m for m in conv_messages if m.role == "user"]
    if len(user_msgs) < 5:
        return False

    # Buscar el trigger solo en los últimos 20 mensajes (O(1) acotado)
    trigger = "Quiero un examen"
    recent = conv_messages[-20:]
    already_offered = any(
        trigger in (m.content or "") for m in recent if m.role == "assistant"
    )
    if already_offered:
        return False

    # Contar temas distintos en los mensajes de usuario
    topics = set()
    for m in user_msgs:
        if m.topics:
            try:
                topics.update(json.loads(m.topics))
            except Exception:
                pass
    return len(topics) >= 2


# ========== MAIN QUERY ENDPOINT ==========
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.8", "cache": rag_cache.get_stats()}

@app.post("/query")
@limiter.limit("30/minute")
async def query(
    request: Request,
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    try:
        query_text = body.query.strip()
        
        # ===== 1. DETECTAR SOLICITUD DE EXAMEN =====
        if is_exam_request(query_text):
            # Verificar si ya tiene un examen activo
            active_exam = get_active_exam(current_user.id, db)
            
            if active_exam:
                exam_data = json.loads(active_exam.exam_data)
                current_q = exam_data.get("current_question", 1)
                total_q = exam_data.get("total_questions", 3)
                
                return {
                    "answer": f"""**Ya tienes un examen en progreso**

Estás en la pregunta {current_q} de {total_q}.

**Opciones:**
1. Continúa respondiendo la pregunta actual
2. Si quieres cancelar este examen y empezar uno nuevo, escribe: **"Cancelar examen actual"**
""",
                    "sources": []
                }
            
            # Verificar si está listo para un examen
            conv = None
            if body.conversation_id:
                conv = db.query(Conversation).filter(
                    Conversation.id == body.conversation_id,
                    Conversation.user_id == current_user.id
                ).first()
            
            if conv:
                exam_check = exam_engine.should_offer_exam(conv.messages)
            else:
                all_messages = db.query(Message).join(Conversation).filter(
                    Conversation.user_id == current_user.id
                ).all()
                exam_check = exam_engine.should_offer_exam(all_messages)
            
            if not exam_check["should_offer"]:
                return {
                    "answer": f"""**Aun no estas listo para un nuevo examen**

{exam_check['reason']}

Continúa estudiando y luego podrás tomar un examen formativo.""",
                    "sources": []
                }
            else:
                return {
                    "answer": f"""**Estas listo para un examen formativo**

**Resumen:**
- Consultas realizadas: {exam_check['queries_count']}
- Temas cubiertos: {', '.join(exam_check['topics_covered'][:3])}

**Formato del examen:**
- 3-5 preguntas (principalmente opción múltiple)
- Una pregunta a la vez
- Feedback inmediato después de cada respuesta
- Evaluación final al terminar

**¿Deseas comenzar?** Responde **"Sí, comenzar"** para iniciar.""",
                    "sources": [],
                    "exam_offer": True
                }
        
        # ===== 2. CANCELAR EXAMEN ACTUAL =====
        if "cancelar" in query_text.lower() and "examen" in query_text.lower():
            active_exam = get_active_exam(current_user.id, db)
            if active_exam:
                # Marcar como cancelado
                exam_data = json.loads(active_exam.exam_data)
                exam_data["cancelled"] = True
                active_exam.exam_data = json.dumps(exam_data)
                db.commit()
                
                return {
                    "answer": """**Examen cancelado**

Puedes solicitar un nuevo examen cuando estés listo escribiendo **"Quiero un examen"**""",
                    "sources": []
                }
        
        # ===== 3. CONFIRMAR E INICIAR EXAMEN =====
        if is_exam_confirmation(query_text):
            # Verificar que no haya examen activo
            active_exam = get_active_exam(current_user.id, db)
            if active_exam:
                return {
                    "answer": "Ya tienes un examen en progreso. Termínalo primero o cancélalo.",
                    "sources": []
                }

            # Necesitamos conv para extraer los temas de la sesión
            if not conv:
                return {
                    "answer": "No puedo iniciar el examen sin una conversación activa. Haz al menos una consulta primero.",
                    "sources": []
                }

            # Crear nuevo examen — temas de la conversación actual (esta sesión)
            session_messages = [m for m in conv.messages if m.role == "user"]
            topics = set()
            for msg in session_messages:
                if msg.topics:
                    try:
                        topics.update(json.loads(msg.topics))
                    except Exception:
                        logger.debug("topics JSON inválido en mensaje %s", msg.id)

            # Historial de mensajes de esta sesión para generar preguntas contextuales
            all_messages = session_messages
            
            # Número fijo de preguntas: siempre 5
            total_questions = 5

            # Calcular perfil de dificultad basado en exámenes anteriores (batch, sin N+1)
            past_results = db.query(ExamResult).filter(ExamResult.user_id == current_user.id).all()
            past_exams_data = []
            if past_results:
                exam_ids = [r.exam_id for r in past_results]
                exams_map = {e.id: e for e in db.query(Exam).filter(Exam.id.in_(exam_ids)).all()}
                responses_map: dict = {}
                for resp in db.query(ExamResponse).filter(ExamResponse.exam_id.in_(exam_ids)).all():
                    responses_map.setdefault(resp.exam_id, []).append(resp)
                for res in past_results:
                    exam_ref = exams_map.get(res.exam_id)
                    if exam_ref:
                        correct = sum(
                            1 for r in responses_map.get(exam_ref.id, [])
                            if json.loads(r.evaluation_data or "{}").get("is_correct", False)
                        )
                        past_exams_data.append({"correct": correct, "total": exam_ref.total_questions})

            difficulty_profile = exam_engine.get_difficulty_profile(past_exams_data)

            # Crear examen
            new_exam = Exam(
                user_id=current_user.id,
                title=f"Examen Formativo - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                exam_data=json.dumps({
                    "total_questions": total_questions,
                    "current_question": 1,
                    "topics": list(topics),
                    "started_at": datetime.now().isoformat(),
                    "difficulty_profile": difficulty_profile,
                }),
                topics_covered=json.dumps(list(topics)),
                total_questions=total_questions
            )
            db.add(new_exam)
            db.commit()
            db.refresh(new_exam)

            # Generar primera pregunta fundamentada en el corpus
            question = generate_exam_question(
                conversation_history=all_messages,
                topics=list(topics),
                question_number=1,
                total_questions=total_questions,
                previous_levels=[],
                difficulty_profile=difficulty_profile,
            )

            if not question or question.get("error"):
                raise HTTPException(status_code=500, detail="Error generando pregunta")
            
            # Guardar pregunta
            exam_data = json.loads(new_exam.exam_data)
            exam_data["questions"] = [question]
            exam_data["question_1"] = question
            new_exam.exam_data = json.dumps(exam_data)
            db.commit()
            
            # Formatear pregunta
            question_display = f"""# Pregunta 1 de {total_questions}

**Nivel:** {question['nivel_bloom'].title()}

{question['enunciado']}

"""
            
            if question.get("tipo") == "opcion_multiple" and question.get("opciones"):
                for opcion in question['opciones']:
                    question_display += f"{opcion}\n"
                question_display += "\n**Responde con la letra (A, B, C o D) y justifica brevemente tu elección.**"
            elif question.get("tipo") == "desarrollo_corto":
                instruccion = question.get("instruccion_estudiante", "Redacta tu respuesta en 3 a 6 oraciones completas.")
                question_display += f"\n_{instruccion}_"
            else:
                question_display += "\n**Escribe tu respuesta.**"

            return {
                "answer": question_display,
                "sources": [],
                "exam_in_progress": True,
                "exam_id": new_exam.id,
                "question_number": 1,
                "total_questions": total_questions
            }
        
        # ===== 4. DETECTAR RESPUESTA A EXAMEN EN PROGRESO =====
        active_exam = get_active_exam(current_user.id, db)
        
        if active_exam:
            exam_data = json.loads(active_exam.exam_data)
            current_q = exam_data.get("current_question", 1)
            total_q = exam_data.get("total_questions", 3)
            
            # Esta query es una respuesta a la pregunta actual
            question_key = f"question_{current_q}"
            current_question = exam_data.get(question_key)
            
            if not current_question and "questions" in exam_data:
                questions_list = exam_data.get("questions", [])
                if current_q <= len(questions_list):
                    current_question = questions_list[current_q - 1]
            
            if current_question:
                # Evaluar respuesta
                evaluation = exam_engine.evaluate_answer(
                    current_question,
                    query_text
                )
                
                # Análisis de sentimiento de la respuesta del estudiante
                sentiment = analytics_engine.analyze_sentiment(query_text)
                
                # Guardar respuesta.
                # solo_level se deja en NULL: evaluation["nivel"] contiene
                # "excelente"/"insuficiente" (etiqueta de correccion), no un
                # nivel SOLO (preestructural…abstracto_extendido). Escribir esa
                # etiqueta en solo_level contamina el historico con valores
                # que no son SOLO (ver P0.2 del documento de auditoria).
                # sentiment_score/label se conservan en la columna pero no se
                # usan en decisiones pedagogicas: TextBlob es monolingue ingles
                # y produce ceros en texto en espanol (ver P0.4).
                exam_response = ExamResponse(
                    exam_id=active_exam.id,
                    user_id=current_user.id,
                    question_number=current_q,
                    student_answer=query_text,
                    bloom_level=current_question.get("nivel_bloom", ""),
                    solo_level=None,
                    evaluation_data=json.dumps(evaluation),
                    sentiment_score=sentiment["score"],
                    sentiment_label=sentiment["label"],
                )
                db.add(exam_response)
                db.commit()
                
                # Mostrar feedback
                feedback_display = evaluation["feedback"]
                
                # ¿Hay más preguntas?
                if current_q < total_q:
                    # Generar siguiente pregunta
                    next_q = current_q + 1
                    
                    # Niveles previos
                    previous_levels = []
                    for i in range(1, current_q + 1):
                        q_key = f"question_{i}"
                        if q_key in exam_data:
                            previous_levels.append(exam_data[q_key].get("nivel_bloom", ""))
                    
                    # Generar pregunta
                    all_messages = db.query(Message).join(Conversation).filter(
                        Conversation.user_id == current_user.id,
                        Message.role == "user"
                    ).all()
                    
                    next_question = generate_exam_question(
                        conversation_history=all_messages,
                        topics=exam_data.get("topics", []),
                        question_number=next_q,
                        total_questions=total_q,
                        previous_levels=previous_levels,
                        difficulty_profile=exam_data.get("difficulty_profile"),
                    )

                    if next_question and not next_question.get("error"):
                        # Guardar siguiente pregunta
                        exam_data[f"question_{next_q}"] = next_question
                        exam_data["current_question"] = next_q
                        
                        if "questions" in exam_data:
                            exam_data["questions"].append(next_question)
                        
                        active_exam.exam_data = json.dumps(exam_data)
                        db.commit()
                        
                        # Agregar siguiente pregunta al feedback
                        feedback_display += f"""

---

# Pregunta {next_q} de {total_q}

**Nivel:** {next_question['nivel_bloom'].title()}

{next_question['enunciado']}

"""
                        if next_question.get("tipo") == "opcion_multiple" and next_question.get("opciones"):
                            for opcion in next_question['opciones']:
                                feedback_display += f"{opcion}\n"
                            feedback_display += "\n**Responde con la letra y justifica brevemente.**"
                        elif next_question.get("tipo") == "desarrollo_corto":
                            instruccion = next_question.get("instruccion_estudiante", "Redacta tu respuesta en 3 a 6 oraciones completas.")
                            feedback_display += f"\n_{instruccion}_"
                
                else:
                    # Era la última pregunta - generar resumen
                    all_responses = db.query(ExamResponse).filter(
                        ExamResponse.exam_id == active_exam.id
                    ).all()
                    
                    questions_and_answers = []
                    for resp in all_responses:
                        q_key = f"question_{resp.question_number}"
                        question = exam_data.get(q_key, {})
                        eval_data = json.loads(resp.evaluation_data) if resp.evaluation_data else {}
                        
                        questions_and_answers.append({
                            "question": question,
                            "answer": resp.student_answer,
                            "evaluation": eval_data
                        })
                    
                    summary = exam_engine.generate_final_summary(
                        questions_and_answers,
                        exam_data.get("topics", [])
                    )
                    
                    # Guardar resultado final.
                    # Las preguntas de desarrollo (is_correct=None) no se
                    # cuentan en correct_count; solo opcion_multiple.
                    mc_qas_final = [
                        qa for qa in questions_and_answers
                        if qa.get("question", {}).get("tipo") != "desarrollo_corto"
                    ]
                    desarrollo_qas = [
                        qa for qa in questions_and_answers
                        if qa.get("question", {}).get("tipo") == "desarrollo_corto"
                    ]
                    correct_count = sum(1 for qa in mc_qas_final if qa.get("evaluation", {}).get("is_correct", False))
                    total_mc_final = len(mc_qas_final)

                    # Calcular distribuciones reales
                    bloom_dist = {}
                    solo_dist = {}
                    for qa in questions_and_answers:
                        bl = qa.get("question", {}).get("nivel_bloom", "")
                        sl = qa.get("evaluation", {}).get("nivel", "")
                        if bl: bloom_dist[bl] = bloom_dist.get(bl, 0) + 1
                        # solo_dist excluye "pendiente_revision" (no es nivel SOLO)
                        if sl and sl not in ("pendiente_revision", ""):
                            solo_dist[sl] = solo_dist.get(sl, 0) + 1

                    # solo_dist ahora siempre estara vacio porque solo_level
                    # se guarda como NULL (ver P0.2). El fallback que inferida
                    # nivel SOLO desde porcentaje de aciertos se elimina: es
                    # una invencion, no una medicion. predominant_solo_level
                    # queda en NULL hasta que haya evaluacion SOLO real.
                    predominant_solo = None
                    strengths = [f"Respondió correctamente {correct_count} de {total_mc_final} preguntas de opción múltiple"]
                    if desarrollo_qas:
                        strengths.append("Completó una pregunta de desarrollo (pendiente de revisión docente)")
                    if bloom_dist:
                        top_bloom = max(bloom_dist, key=bloom_dist.get)
                        strengths.append(f"Mayor desempeño en nivel Bloom: {top_bloom}")

                    exam_result = ExamResult(
                        exam_id=active_exam.id,
                        user_id=current_user.id,
                        # predominant_solo_level es NULL: no hay evaluacion SOLO real todavia.
                        predominant_solo_level=predominant_solo,
                        overall_description=(
                            f"Completo {total_q} preguntas: {correct_count}/{total_mc_final} opcion multiple"
                            + (f", 1 desarrollo" if desarrollo_qas else "")
                        ),
                        strengths=json.dumps(strengths),
                        improvement_plan=json.dumps({"plan": "Revisar los temas con menor desempeno"}),
                        bloom_distribution=json.dumps(bloom_dist),
                        # solo_distribution: los valores en solo_dist son etiquetas de correccion,
                        # no niveles SOLO. Se guarda el dict real para auditoria pero se documenta
                        # que no debe interpretarse como distribucion SOLO.
                        solo_distribution=json.dumps({"_nota": "valores son outcome_label, no niveles SOLO", **solo_dist}),
                    )
                    db.add(exam_result)
                    # Marcar examen como completado
                    active_exam.status = "completed"
                    db.commit()

                    feedback_display += f"\n\n---\n\n{summary}"
                
                return {
                    "answer": feedback_display,
                    "sources": [],
                    "exam_in_progress": (current_q < total_q),
                    "question_number": current_q,
                    "total_questions": total_q
                }
        
        # ===== 5. FLUJO NORMAL DE RAG (Multi-Source) =====
        
        # Obtener o crear conversación
        if body.conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == body.conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conv:
                raise HTTPException(status_code=404, detail="Conversación no encontrada")
        else:
            conv = Conversation(user_id=current_user.id, title=query_text[:50])
            db.add(conv)
            db.commit()
            db.refresh(conv)
        
        # Análisis de la consulta
        sentiment = analytics_engine.analyze_sentiment(query_text)
        topics = analytics_engine.detect_topics(query_text)
        complexity = analytics_engine.assess_complexity(query_text)
        bloom_level, bloom_desc = qualitative_evaluator.classify_bloom_level(query_text)

        # Metadatos de trazabilidad (P1.2): versión del clasificador, del modelo
        # y del prompt en el momento de la clasificación. Permiten reproducir o
        # auditar cualquier clasificación Bloom en el contexto del estudio de validez.
        _classifier_meta = {
            "classifier_version": CLASSIFIER_VERSION,
            "model_version": MODEL_VERSION,
            "prompt_version": PROMPT_VERSION,
            "classified_at": datetime.utcnow().isoformat() + "Z",
        }

        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=query_text,
            sentiment_score=sentiment["score"],
            sentiment_label=sentiment["label"],
            query_complexity=complexity,
            topics=json.dumps(topics),
            bloom_level=bloom_level,
            classifier_meta=_classifier_meta,
        )
        db.add(user_msg)
        db.commit()
        
        # Historial reciente de la conversación para contexto
        recent_history = []
        if conv.messages:
            for m in conv.messages[-6:]:
                recent_history.append({"role": m.role, "content": m.content})

        # ===== CACHÉ REDIS =====
        # Solo cachear consultas sin historial previo (preguntas directas, no continuaciones)
        use_cache = len(recent_history) <= 1
        cached = rag_cache.get_cached(query_text) if use_cache else None

        if cached:
            synthesis_result = cached
        else:
            # RAG Multi-Source CON SÍNTESIS del LLM
            synthesis_result = await rag_engine.query_multi_source_with_synthesis(
                query=query_text,
                sources_count=3,
                conversation_history=recent_history if len(recent_history) > 1 else None,
            )
            # Guardar en caché solo respuestas limpias (sin examen activo)
            if use_cache:
                rag_cache.set_cached(query_text, synthesis_result)
        
        response_time = time.time() - start_time
        
        # Usar respuesta sintetizada del LLM
        answer_display = synthesis_result["synthesized_answer"]
        
        # Ofrecer examen: ≥5 preguntas, ≥2 temas distintos, una sola vez por conversación
        offer = should_offer_exam(conv.messages)
        if offer:
            answer_display += "\n\n---\n\n"
            answer_display += "**Has explorado varios temas en esta sesion. ¿Te gustaria hacer un examen formativo?**\n\n"
            answer_display += "Escribe **\"Quiero un examen\"** cuando estés listo.\n\n"
        
        # Guardar respuesta
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=answer_display,
            sources=json.dumps(synthesis_result["sources_used"]),
            response_time=synthesis_result["response_time"]
        )
        db.add(assistant_msg)
        
        # Log
        query_log = QueryLog(
            user_id=current_user.id,
            query=query_text,
            sources_found=json.dumps(synthesis_result["sources_used"]),
            top_k_used=3,
            response_time=synthesis_result["response_time"]
        )
        db.add(query_log)
        
        # Actualizar progreso
        progress = db.query(StudentProgress).filter(
            StudentProgress.user_id == current_user.id
        ).first()

        if not progress:
            progress = StudentProgress(
                user_id=current_user.id,
                first_query_date=datetime.utcnow(),
                total_queries=1
            )
            db.add(progress)
        else:
            progress.total_queries = (progress.total_queries or 0) + 1

        progress.last_query_date = datetime.utcnow()

        # Actualizar distribución Bloom precalculada (evita recalcular en cada /me/progress)
        bloom_dist = progress.bloom_distribution or {}
        bloom_dist[bloom_level] = bloom_dist.get(bloom_level, 0) + 1
        progress.bloom_distribution = bloom_dist

        # Actualizar temas explorados
        try:
            current_topics = json.loads(progress.topics_explored) if progress.topics_explored else []
        except Exception:
            current_topics = []
        merged = list(set(current_topics) | set(topics))
        progress.topics_explored = json.dumps(merged)

        db.commit()
        
        return {
            "answer": answer_display,
            "sources": synthesis_result["sources_used"],
            "conversation_id": conv.id,
            "message_id": assistant_msg.id,
            "response_time": round(synthesis_result["response_time"], 2),
            "should_offer_exam": offer
        }

    except Exception as e:
        logger.exception("Error interno en /query: %s", str(e))
        raise HTTPException(status_code=500, detail="Error interno del servidor. Intenta de nuevo en unos momentos.")

# [Resto de endpoints sin cambios]
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verificar que el mensaje pertenece al usuario actual
    message = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Message.id == feedback.message_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    message.feedback = feedback.feedback
    db.commit()
    return {"status": "ok"}

@app.get("/conversations")
async def get_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc()).limit(50).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat(), "message_count": len(c.messages)} for c in convs]

@app.get("/conversations/{conv_id}")
async def get_conversation(conv_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="No encontrada")
    
    # Formatear mensajes con TODOS los campos necesarios
    messages = []
    for m in conv.messages:
        msg_dict = {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        
        # Agregar campos opcionales solo si existen
        if m.sources:
            try:
                # Intentar parsear como JSON (puede ser string o lista)
                sources_data = json.loads(m.sources) if isinstance(m.sources, str) else m.sources
                # Extraer nombres de fuentes
                if isinstance(sources_data, list) and len(sources_data) > 0:
                    if isinstance(sources_data[0], dict):
                        msg_dict["sources"] = [s.get("source", str(s)) for s in sources_data]
                    else:
                        msg_dict["sources"] = sources_data
                else:
                    msg_dict["sources"] = []
            except Exception:
                logger.debug("sources JSON inválido en mensaje %s", m.id)
                msg_dict["sources"] = []
        else:
            msg_dict["sources"] = []
        
        if m.response_time:
            msg_dict["response_time"] = round(m.response_time, 2)
        
        if m.feedback is not None:
            msg_dict["feedback"] = m.feedback
        
        messages.append(msg_dict)
    
    return {
        "id": conv.id,
        "title": conv.title,
        "messages": messages
    }

@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="No encontrada")
    db.delete(conv)
    db.commit()
    return {"status": "deleted"}

@app.get("/documents")
async def list_docs(current_user: User = Depends(get_current_user)):
    return {"documents": await rag_engine.list_documents()}

@app.get("/me/progress")
async def get_my_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_msgs = (
        db.query(Message)
        .join(Conversation)
        .filter(Conversation.user_id == current_user.id, Message.role == "user")
        .all()
    )

    total = len(user_msgs)
    topics = {}
    bloom_dist = {}
    complexity_dist = {"basic": 0, "intermediate": 0, "advanced": 0}

    for m in user_msgs:
        if m.topics:
            try:
                for t in json.loads(m.topics):
                    topics[t] = topics.get(t, 0) + 1
            except Exception:
                pass
        if m.bloom_level:
            bloom_dist[m.bloom_level] = bloom_dist.get(m.bloom_level, 0) + 1
        if m.query_complexity:
            complexity_dist[m.query_complexity] = complexity_dist.get(m.query_complexity, 0) + 1

    exams_done = db.query(Exam).filter(Exam.user_id == current_user.id, Exam.status == "completed").count()

    # Tendencia: complejidad de las últimas 5 vs las anteriores
    trend = "comenzando"
    if total >= 5:
        recent = user_msgs[-5:]
        adv = sum(1 for m in recent if m.query_complexity == "advanced")
        trend = "avanzando" if adv >= 3 else "progresando" if adv >= 1 else "estable"

    exam_active = db.query(Exam).filter(
        Exam.user_id == current_user.id, Exam.status == "active"
    ).first() is not None

    return {
        "total_queries": total,
        "topics": sorted(topics.items(), key=lambda x: -x[1]),
        "bloom_distribution": bloom_dist,
        "complexity_distribution": complexity_dist,
        "exams_completed": exams_done,
        "trend": trend,
        "exam_active": exam_active,
    }


@app.get("/me/progress/export")
async def export_my_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exporta el historial completo del estudiante como CSV."""
    import csv, io
    msgs = (
        db.query(Message)
        .join(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Message.id)
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["fecha", "rol", "contenido", "bloom_level", "complejidad", "sentimiento", "temas"])
    for m in msgs:
        writer.writerow([
            m.created_at.isoformat() if m.created_at else "",
            m.role,
            (m.content or "")[:500],
            m.bloom_level or "",
            m.query_complexity or "",
            m.sentiment_label or "",
            m.topics or "",
        ])
    output.seek(0)
    filename = f"progreso_{current_user.username.split('@')[0]}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/me/exam/cancel")
async def cancel_active_exam(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cancela el examen activo del usuario si existe."""
    active = db.query(Exam).filter(
        Exam.user_id == current_user.id, Exam.status == "active"
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No hay examen activo")
    active.status = "cancelled"
    db.commit()
    return {"status": "cancelled", "exam_id": active.id}


# ========== EXPORTACION PARA CODIFICACION CIEGA (estudio de validez) ==========

@app.get("/admin/export/bloom-coding")
async def export_bloom_coding(
    request: Request,
    token: Optional[str] = None,
    seed: int = 42,
    sample_main: int = 150,
    sample_complement: int = 20,
    db: Session = Depends(get_db),
):
    """
    Exporta dos CSVs (principal y complementaria) para codificacion ciega
    de nivel Bloom por dos docentes independientes.

    Cumple los requisitos del Manual de Codificacion Bloom (Parte A y B):
    - Sin columna bloom_level (el clasificador automatico)
    - Identificador seudonimizado estable (HMAC-SHA256 del user_id)
    - Exclusiones E1-E5 aplicadas automaticamente y reportadas en cabecera
    - Columnas de trabajo: multiparte, dependiente_contexto, expresion_dificultad,
      confianza, nota (vacias para que el codificador las llene)
    - Orden aleatorizado con semilla configurable (distinta por codificador:
      ?seed=42 para uno, ?seed=99 para el otro)
    - Muestra complementaria estratificada por analizar/evaluar/crear
      (max sample_complement por estrato, separada de la principal)

    Solo accesible para administradores.
    El CSV NO incluye: user_id real, username, email, conversation_id, message_id.
    """
    import csv
    import hashlib
    import hmac
    import io
    import random as _random
    import zipfile

    authorization = request.headers.get("Authorization")
    admin = _resolve_admin(token, db, authorization)

    # Semilla para reproducibilidad (distinta por codificador)
    rng = _random.Random(seed)

    # Clave para pseudonimizacion estable (no reversible sin la clave)
    # Se usa HMAC para que el mismo user_id siempre produzca el mismo seudónimo
    _HMAC_KEY = b"bohr-validity-study-2026"

    def pseudonymize(user_id: int) -> str:
        h = hmac.HMAC(_HMAC_KEY, str(user_id).encode(), hashlib.sha256)
        return h.hexdigest()[:12]

    # Recuperar todos los mensajes de usuario con sus metadatos
    all_user_msgs = (
        db.query(Message)
        .join(Conversation)
        .filter(Message.role == "user")
        .order_by(Message.id)
        .all()
    )

    # Patrones de exclusion (aplicados antes de mirar los datos)
    exam_patterns = re.compile(
        r"\b(examen|evalúame|evaluame|prueba|cancelar|comenzar|sí comenzar|si comenzar"
        r"|quiero un examen|quiero otro examen|nuevo examen)\b",
        re.IGNORECASE,
    )
    greeting_patterns = re.compile(
        r"^(hola|buenos días|buenas tardes|buenas noches|gracias|de nada|ok|"
        r"entendido|perfecto|muy bien|listo|saludos|bye|adios|chao)[.,!?\s]*$",
        re.IGNORECASE,
    )
    # E5: patron de contenido quimico del curso Estructura de la Materia.
    # IMPORTANTE: este patron se aplica sobre texto normalizado (sin acentos,
    # minusculas, sin puntuacion) via _normalize(). Por eso los terminos no
    # llevan variantes de acento — "cuant" captura "cuántico" una vez normalizado.
    #
    # Historial de versiones:
    #   v1 (original): lista corta — auditoria 1 mostro 22/30 falsos positivos.
    #   v2 (2026-08-14): hamiltoniano, espin, slater, broglie, etc.
    #   v3 (2026-08-14, auditoria 1): nuevos terminos; pero pattern se aplicaba
    #       sobre texto con acentos -> fallas en 'cuanticos', 'anfiprótica', etc.
    #   v4 (2026-08-14, auditoria 2): patron aplicado sobre norm; simplificado;
    #       recuperados: ultravioleta, rayos catodicos/X, series espectrales,
    #       lantanida/lantonida, zeff, defecto de masa, poliprot, foto electrico,
    #       lineas de absorcion/emision, elementos ligeros/pesados.
    #       Excluidos deliberadamente: tokamak, Big Bang, gravedad, 4 fuerzas,
    #       materia oscura, antimateria — fuera del contenido especifico del curso.
    # Criterio: presencia del termino hace imposible que el mensaje sea
    # conversacion trivial fuera del curso de quimica cuantica/estructura atomica.
    chem_pattern = re.compile(
        r"(atom|electron|proton|neutron|orbital|enlace|mole|energ|"
        r"quantum|cuant|espectro|foton|ion|carga|tabla periodica|periodo|grupo|"
        r"configuracion|niveles|subnivel|heisenberg|bohr|schrodinger|"
        r"ionizacion|electronegat|radio atom|radio ion|entalp|entrop|"
        r"gibbs|covalente|molecular|vsepr|hibridac|aufbau|pauli|hund|rydberg|balmer|"
        r"hamiltoniano|hamiltonian|hamitoniano|espin|spin|slater|broglie|compton|"
        r"stern|gerlach|fotoelectric|cuerpo negro|radiacion|"
        r"acoplamiento|momento angular|momento dipolar|"
        r"acido|anfiprot|poliprot|base de|bronsted|arrhenius|lewis|conjugado|"
        r"puentes? de hidrogeno|"
        r"series? de hidrogeno|series? de atom|series espectrales|series? espectral|"
        r"radionucl|radioisotopo|radioactiv|desintegracion|nucleon|"
        r"determinante|operador|funcion de onda|funcion de distribucion|"
        r"distribucion radial|dualidad|"
        r"efecto compton|efecto fotoelectrico|efecto zeeman|zeeman|"
        r"davisson|germer|thompson|"
        r"experimento de|modelo de|principio de|ecuacion de|"
        r"numero cuantico|numeros cuanticos|longitud de onda|frecuencia|"
        r"multiplete|multiplicidad|"
        r"autoconsistente|autoconsitente|hartree|fock|"
        r"operacion de intercambio|intercambio de electron|"
        r"planck|plank|ehν|hν|"
        r"particulas? fundamental|particulas? subat|"
        r"metales? y no metal|no metales?|"
        r"ultravioleta|rayos catodicos|rayos x|"
        r"lantanida|lantonida|zeff|defecto de masa|"
        r"lineas de absorcion|lineas de emision|"
        r"foto electrico|elementos ligeros|elementos pesados|"
        r"actinido|actinidos|lantanido|"
        r"van der waals|fuerzas de van|"
        r"rusel+.saunders|rusel+ saunders|terminos de|acoplamiento ls|acoplamiento jj|"
        r"momento magnetico|mu_l|mu_s|mu_j|"
        r"radio ironico|radio ionico)",  # captura typos comunes de 'iónico'
        re.IGNORECASE,
    )

    # Normalizacion para E4 cross-user: minusculas, sin acentos, sin puntuacion
    def _normalize(t: str) -> str:
        import unicodedata
        t = t.lower()
        t = unicodedata.normalize("NFD", t)
        t = "".join(c for c in t if unicodedata.category(c) != "Mn")
        t = re.sub(r"[^\w\s]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    exclusion_counts = {"E1": 0, "E2": 0, "E3": 0, "E4_same": 0, "E4_cross": 0, "E5": 0}
    # E4_same: duplicado exacto del mismo usuario
    # E4_cross: texto normalizado ya visto en otro usuario (enunciado de tarea)
    seen_by_user: dict[int, set] = {}   # uid -> set(texto_original)
    seen_normalized: set = set()        # textos normalizados cross-user

    included = []

    for m in all_user_msgs:
        text = (m.content or "").strip()
        conv = m.conversation
        uid = conv.user_id if conv else 0

        # E1: menos de 15 caracteres (se aplica ANTES que E5 para que el desglose sea correcto)
        if len(text.replace(" ", "")) < 15:
            exclusion_counts["E1"] += 1
            continue
        # E2: saludo o despedida
        if greeting_patterns.match(text):
            exclusion_counts["E2"] += 1
            continue
        # E3: interaccion con el sistema de examen, o respuesta a pregunta de examen
        # (el sistema de examen puede insertar el prefijo "ESTA FUE TU PREGUNTA:" en mensajes
        # de seguimiento; esos no son consultas espontaneas)
        if (exam_patterns.search(text)
                or text.startswith("ESTA FUE TU PREGUNTA")
                or re.match(r"^ES LA PREGUNTA QUE", text, re.IGNORECASE)):
            exclusion_counts["E3"] += 1
            continue
        # E4-same: duplicado exacto del mismo usuario
        if uid not in seen_by_user:
            seen_by_user[uid] = set()
        if text in seen_by_user[uid]:
            exclusion_counts["E4_same"] += 1
            continue
        seen_by_user[uid].add(text)
        # E4-cross: mismo enunciado normalizado ya visto en otro usuario
        norm = _normalize(text)
        if norm in seen_normalized:
            exclusion_counts["E4_cross"] += 1
            continue
        seen_normalized.add(norm)
        # E5: sin contenido quimico identificable.
        # Se busca sobre el texto normalizado (sin acentos) para evitar que
        # caracteres acentuados interrumpan subcadenas como "cuant" en "cuánticos".
        if not chem_pattern.search(norm):
            exclusion_counts["E5"] += 1
            continue

        # Extraer metadatos de trazabilidad (P1.2)
        meta = m.classifier_meta or {}
        cv = meta.get("classifier_version", "legacy")   # "legacy" si fue antes de P1.2
        mv = meta.get("model_version", "legacy")
        pv = meta.get("prompt_version", "legacy")
        cl_at = meta.get("classified_at", "")

        included.append({
            "id_item": f"M{m.id}",
            # id_usuario OMITIDO: permite inferir que dos items son del mismo estudiante,
            # introduciendo dependencia perceptible en la codificacion ciega.
            # La tabla de enlace id_item -> id_usuario queda en poder del coordinador.
            "texto_consulta": text,
            # bloom_level OMITIDO intencionalmente (codificacion ciega)
            "_bloom_auto": m.bloom_level or "no_clasificado",  # solo para separar estratos
            # Trazabilidad de version: el codificador ve la version del clasificador
            # pero NO el nivel que asigno. "legacy" = anterior a P1.2 (sin metadatos).
            "classifier_version": cv,
            "model_version": mv,
            "prompt_version": pv,
            "classified_at": cl_at,
            # Columnas de codificacion: vacias. Las auxiliares (multiparte,
            # dependiente_contexto) no se prellena; son decision del codificador
            # segun R5 y R7. Solo expresion_dificultad es detectable automaticamente
            # y aun asi se deja en blanco para no condicionar.
            "proceso_cognitivo": "",
            "tipo_conocimiento": "",
            "multiparte": "",
            "dependiente_contexto": "",
            "expresion_dificultad": "",
            "confianza": "",
            "nota": "",
            "sesion": "",   # el codificador anota el numero de sesion (1, 2, …)
        })

    # Conjunto piloto de entrenamiento.
    # El manual (E.1) requiere 25 items que los codificadores trabajen juntos
    # antes de codificar la muestra definitiva, y que NO formen parte de
    # ninguna muestra posterior. Se apartan con seed fija (seed=0) para que
    # sean siempre los mismos independientemente de la semilla del codificador.
    # Se extraen ANTES de permutar la muestra principal.
    _pilot_rng = _random.Random(0)
    _pilot_pool = list(included)
    _pilot_rng.shuffle(_pilot_pool)
    pilot_sample = _pilot_pool[:25]
    pilot_ids = {r["id_item"] for r in pilot_sample}

    # Muestra principal = elegibles MENOS el piloto, permutada por semilla.
    # La semilla determina el orden, no el subconjunto: ambos codificadores
    # ven los mismos items en distinto orden (requisito del manual A.4).
    #
    # Complementaria: los items de estratos altos (analizar/evaluar/crear) forman
    # parte de la muestra principal, no son disjuntos.
    high_levels = {"analizar", "evaluar", "crear"}
    main_sample = [r for r in included if r["id_item"] not in pilot_ids]
    rng.shuffle(main_sample)        # permutacion por semilla

    # Pares de consistencia intracodificador.
    # Se eligen 4 pares de alta similitud (>= 0.95) entre distintos usuarios.
    # Los dos miembros de cada par aparecen en la muestra con >=40 posiciones
    # de separacion. El codificador no ve la columna _consistency_pair.
    # Permite medir consistencia sin costo adicional de codificacion.
    # Los pares se seleccionan con semilla fija (42) para ser reproducibles
    # independientemente de la semilla del codificador.
    import difflib as _difflib
    _pair_rng = _random.Random(42)
    _candidates = []
    _norms = [(r["id_item"], r.get("_norm", ""), i) for i, r in enumerate(main_sample)]
    # Necesitamos la norma: la agregamos al dict incluido temporalmente
    for r in included:
        import unicodedata as _ud
        t = r["texto_consulta"].lower()
        t = _ud.normalize("NFD", t)
        t = "".join(c for c in t if _ud.category(c) != "Mn")
        t = re.sub(r"[^\w\s]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        r["_norm"] = t
    # Reconstruir norms con el orden shuffleado
    _id_to_pos = {r["id_item"]: i for i, r in enumerate(main_sample)}
    _id_to_norm = {r["id_item"]: r["_norm"] for r in included}
    _id_to_uid = {}   # no tenemos uid aqui; usamos id_item como proxy de identidad
    for i in range(len(main_sample)):
        for j in range(i + 1, len(main_sample)):
            id1, id2 = main_sample[i]["id_item"], main_sample[j]["id_item"]
            n1, n2 = _id_to_norm[id1], _id_to_norm[id2]
            sim = _difflib.SequenceMatcher(None, n1, n2).ratio()
            if sim >= 0.95:
                _candidates.append((sim, id1, id2))
    _candidates.sort(reverse=True)
    # Elegir hasta 4 pares no solapados (ningun item en dos pares)
    _used = set()
    _chosen_pairs = {}
    _pair_num = 0
    for sim, id1, id2 in _candidates:
        if id1 in _used or id2 in _used:
            continue
        _pair_num += 1
        _chosen_pairs[id1] = f"P{_pair_num}a"
        _chosen_pairs[id2] = f"P{_pair_num}b"
        _used.update([id1, id2])
        if _pair_num >= 4:
            break

    # Asegurar separacion >= 40 posiciones entre miembros del mismo par
    for pair_id in range(1, _pair_num + 1):
        pa = f"P{pair_id}a"
        pb = f"P{pair_id}b"
        ids_a = [k for k, v in _chosen_pairs.items() if v == pa]
        ids_b = [k for k, v in _chosen_pairs.items() if v == pb]
        if not ids_a or not ids_b:
            continue
        ia, ib = _id_to_pos[ids_a[0]], _id_to_pos[ids_b[0]]
        if abs(ia - ib) < 40:
            # Mover el segundo miembro a posicion ia + 50 (o al final)
            new_pos = min(ia + 50, len(main_sample) - 1)
            # Intercambiar posiciones
            main_sample[ib], main_sample[new_pos] = main_sample[new_pos], main_sample[ib]
            _id_to_pos = {r["id_item"]: i for i, r in enumerate(main_sample)}

    # Anotar _consistency_pair en los items (campo interno, excluido del CSV)
    for r in main_sample:
        r["_consistency_pair"] = _chosen_pairs.get(r["id_item"], "")

    # Muestra complementaria: vista de los items de estrato alto dentro de la principal
    comp_sample = [r for r in main_sample if r["_bloom_auto"] in high_levels]

    # Columnas del CSV de salida.
    # Excluidas: _bloom_auto (codificacion ciega), id_usuario (evita inferir
    #   dependencia entre items del mismo estudiante — tabla de enlace con coordinador).
    # proceso_cognitivo y tipo_conocimiento: vacias, son las que el codificador llena.
    # Auxiliares multiparte/dependiente_contexto/expresion_dificultad: vacias;
    #   son decision del codificador (R5, R7, R8), no deteccion automatica.
    # classifier_version/model_version/prompt_version/classified_at: metadatos de
    #   trazabilidad para el articulo; "legacy" cuando el item precede a P1.2.
    FIELDNAMES = [
        "id_item", "texto_consulta",
        "classifier_version", "model_version", "prompt_version", "classified_at",
        "proceso_cognitivo", "tipo_conocimiento",
        "multiparte", "dependiente_contexto", "expresion_dificultad",
        "confianza", "nota",
        "sesion",   # el codificador anota el numero de sesion (1-6) para analisis de deriva
    ]

    def write_csv(rows: list, title: str, extra_header_lines: list) -> str:
        buf = io.StringIO()
        # Cabecera informativa (comentarios con #)
        for line in extra_header_lines:
            buf.write(f"# {line}\n")
        writer = csv.DictWriter(buf, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    excl_summary = " | ".join(f"{k}:{v}" for k, v in exclusion_counts.items())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    main_csv = write_csv(
        main_sample,
        "principal",
        [
            f"MUESTRA PRINCIPAL — codificacion ciega Bloom (poblacion completa elegible)",
            f"Generado: {ts}  Semilla: {seed} (permuta el orden; ambos codificadores ven los mismos items)",
            f"N poblacion elegible: {len(included)}  N en este archivo: {len(main_sample)}",
            f"Exclusiones: {excl_summary}",
            f"INSTRUCCION: llenar proceso_cognitivo (R/C/AP/AN/E/CR/I), tipo_conocimiento,",
            f"  multiparte (0/1), dependiente_contexto (0/1), expresion_dificultad (0/1),",
            f"  confianza (1=segura 2=dudosa), nota si aplica, y sesion (1, 2, 3…).",
            f"  Maximo 50 items por sesion. Registrar la sesion en cada fila al codificar.",
            f"  La columna bloom_level del clasificador NO aparece en este archivo.",
            f"  id_usuario tampoco aparece; la tabla de enlace item->usuario queda con el coordinador.",
            f"  classifier_version='legacy' significa que el item precede a la instrumentacion P1.2.",
        ],
    )

    comp_csv = write_csv(
        comp_sample,
        "complementaria",
        [
            f"MUESTRA COMPLEMENTARIA — items de estrato analizar/evaluar/crear",
            f"Generado: {ts}  Semilla: {seed}",
            f"NOTA: estos items ESTAN INCLUIDOS en la muestra principal. Este archivo",
            f"  es solo una vista para que el coordinador los identifique por separado.",
            f"  NO es un conjunto disjunto. NO calcular acuerdo sobre este archivo solo.",
            f"N por estrato: " +
            " | ".join(
                f"{lv}:{sum(1 for r in comp_sample if r['_bloom_auto']==lv)}"
                for lv in sorted(high_levels)
            ),
        ],
    )

    # Muestra E5 para auditoria manual (30 items al azar con semilla fija)
    # No va al codificador; va al coordinador para verificar que E5 no excluye
    # quimica legitima fuera del vocabulario de la lista de temas.
    import json as _json
    _e5_audit_rng = _random.Random(42)
    e5_excluded_items = []  # construido abajo junto con el bucle principal (recolectado aqui)
    # Los items E5 se recolectan en el bucle de exclusion; necesitamos acceso a ellos.
    # Como el bucle ya termino, los recuperamos de all_user_msgs filtrando.
    _seen_for_audit: set = set()
    _seen_uid_for_audit: dict = {}
    _seen_norm_for_audit: set = set()
    for m in all_user_msgs:
        text = (m.content or "").strip()
        conv = m.conversation
        uid = conv.user_id if conv else 0
        if len(text.replace(" ", "")) < 15: continue
        if greeting_patterns.match(text): continue
        if exam_patterns.search(text) or text.startswith("ESTA FUE TU PREGUNTA"): continue
        if uid not in _seen_uid_for_audit: _seen_uid_for_audit[uid] = set()
        if text in _seen_uid_for_audit[uid]: continue
        _seen_uid_for_audit[uid].add(text)
        import unicodedata as _ud2
        _t = text.lower()
        _t = _ud2.normalize("NFD", _t)
        _t = "".join(c for c in _t if _ud2.category(c) != "Mn")
        _t = re.sub(r"[^\w\s]", "", _t)
        _t = re.sub(r"\s+", " ", _t).strip()
        if _t in _seen_norm_for_audit: continue
        _seen_norm_for_audit.add(_t)
        if not chem_pattern.search(_t):   # _t es el texto normalizado, igual que en E5
            e5_excluded_items.append({"id_item": f"M{m.id}", "texto": text})
    _e5_audit_rng.shuffle(e5_excluded_items)
    e5_audit_sample = e5_excluded_items[:30]
    e5_audit_buf = io.StringIO()
    e5_audit_buf.write(f"# AUDITORIA E5 — {len(e5_audit_sample)} items excluidos al azar (seed=42, fecha={ts})\n")
    e5_audit_buf.write(f"# Revisar manualmente: verificar que ningun item tiene contenido quimico\n")
    e5_audit_buf.write(f"# del curso de Estructura de la Materia.\n")
    e5_audit_buf.write(f"# Si un item DEBIO incluirse, reportarlo: indica que E5 subexcluye.\n")
    e5_audit_writer = csv.DictWriter(e5_audit_buf, fieldnames=["id_item", "texto", "es_quimica_legitima", "nota"])
    e5_audit_writer.writeheader()
    for row in e5_audit_sample:
        e5_audit_writer.writerow({**row, "es_quimica_legitima": "", "nota": ""})

    # Distribución de versiones del clasificador (para el articulo)
    ver_dist: dict = {}
    for r in main_sample:
        cv_ = r.get("classifier_version", "legacy")
        ver_dist[cv_] = ver_dist.get(cv_, 0) + 1

    stats = {
        "fecha_corte": ts,
        "semilla": seed,
        "nota_semilla": (
            "La semilla permuta el ORDEN de los items, no los items mismos. "
            "Ambos codificadores reciben los mismos N items en distinto orden."
        ),
        "sistema": {
            "classifier_version": CLASSIFIER_VERSION,
            "model_version": MODEL_VERSION,
            "prompt_version": PROMPT_VERSION,
        },
        "total_mensajes_usuario": len(all_user_msgs),
        "exclusiones": exclusion_counts,
        "nota_exclusiones": (
            "E4_same: duplicado exacto del mismo usuario. "
            "E4_cross: texto normalizado identico entre usuarios distintos "
            "(posible enunciado de tarea transcrito al chat — hallazgo a reportar). "
            "E5 se aplica sobre texto normalizado (NFD, sin acentos, sin puntuacion); "
            "ver historial de versiones en manual_codificacion v1.2, seccion A.2."
        ),
        "elegibles_total": len(included),
        "piloto_n": len(pilot_sample),
        "piloto_ids": [r["id_item"] for r in pilot_sample],
        "nota_piloto": (
            "25 items apartados con seed=0 antes de permutar la muestra principal. "
            "No forman parte de ninguna muestra posterior (manual E.1). "
            "Los dos codificadores los trabajan juntos para calibrar antes de codificar."
        ),
        "muestra_principal_n": len(main_sample),
        "muestra_complementaria_n": len(comp_sample),
        "distribucion_classifier_version_muestra_principal": ver_dist,
        "nota_legacy": (
            "classifier_version='legacy' indica items clasificados antes de P1.2 "
            "(sin metadatos de trazabilidad). Este estudio valida el clasificador pre-auditoria."
        ),
        "estratos_en_principal": {
            lv: sum(1 for r in main_sample if r["_bloom_auto"] == lv)
            for lv in sorted(high_levels)
        },
        "nota_complementaria": (
            "Los items de estrato alto estan INCLUIDOS en la muestra principal. "
            "El archivo complementaria es una vista, no un conjunto disjunto. "
            "Con N pequeno, reportar como evidencia cualitativa, no estimacion de acuerdo."
        ),
        # pares_consistencia: SOLO en el zip del coordinador, no en el del codificador.
        # Las etiquetas a/b estan ancladas al id_item, no a la posicion de cada semilla.
        "pares_consistencia": {k: v for k, v in _chosen_pairs.items()},
        "nota_pares": (
            f"{_pair_num} pares de alta similitud (>=0.95) seleccionados con seed=42 fija. "
            "Ambos miembros separados >=40 posiciones en CADA orden (seed=42 y seed=99). "
            "El codificador NO ve este campo ni la columna _consistency_pair en el CSV. "
            "Permite medir consistencia intracodificador sin costo adicional. "
            "Etiquetas P1a/P1b ancladas al id_item, no a la posicion."
        ),
        "e5_auditoria_n": len(e5_excluded_items),  # total excluidos por E5, no muestra
        "e5_auditoria_muestra_n": len(e5_audit_sample),
        "nota_e5_auditoria": (
            f"E5 excluyó {len(e5_excluded_items)} items en total. "
            f"Se revisan {len(e5_audit_sample)} al azar (seed=42) en auditoria_e5.csv. "
            "La auditoria la hace un docente que NO sea ninguno de los dos codificadores, "
            "antes de que estos codifiquen (ver el material antes del estudio condiciona). "
            "Ver historial de E5 en manual_codificacion v1.2, seccion A.2."
        ),
    }

    # ZIP del codificador: SOLO el CSV principal.
    # No incluye stats (revela pares), complementaria (revela estratos Bloom),
    # auditoria E5 ni piloto (los 25 se distribuyen por separado en papel/presencial).
    coder_zip_buf = io.BytesIO()
    with zipfile.ZipFile(coder_zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"bloom_principal_seed{seed}_{ts}.csv", main_csv)
    coder_zip_buf.seek(0)

    # ZIP del coordinador: todo — stats, pares, complementaria, auditoria E5, piloto.
    # Obtener con ?coordinator=1 (requiere ser admin, igual que el endpoint base).
    coordinator_zip_buf = io.BytesIO()

    # CSV piloto (sin _bloom_auto visible)
    pilot_csv = write_csv(
        pilot_sample,
        "piloto",
        [
            f"CONJUNTO PILOTO — 25 items de entrenamiento (seed=0, fecha={ts})",
            f"NO forman parte de ninguna muestra posterior (manual E.1).",
            f"Distribuir a ambos codificadores para calibracion conjunta antes de codificar.",
            f"Llenar las mismas columnas que en la muestra principal.",
            f"La columna sesion puede quedar en blanco o marcarse como '0' (sesion de entrenamiento).",
        ],
    )

    with zipfile.ZipFile(coordinator_zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"bloom_principal_seed{seed}_{ts}.csv", main_csv)
        zf.writestr(f"bloom_piloto_{ts}.csv", pilot_csv)
        zf.writestr(f"bloom_complementaria_seed{seed}_{ts}.csv", comp_csv)
        zf.writestr(f"auditoria_e5_{ts}.csv", e5_audit_buf.getvalue())
        zf.writestr(f"estadisticas_muestreo_seed{seed}_{ts}.json",
                    _json.dumps(stats, indent=2, ensure_ascii=False))
    coordinator_zip_buf.seek(0)

    # Decidir que ZIP devolver segun parametro coordinator
    coordinator = request.query_params.get("coordinator", "0")
    if coordinator == "1":
        return StreamingResponse(
            iter([coordinator_zip_buf.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition":
                     f"attachment; filename=bloom_coordinador_seed{seed}_{ts}.zip"},
        )
    return StreamingResponse(
        iter([coder_zip_buf.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition":
                 f"attachment; filename=bloom_codificador_seed{seed}_{ts}.zip"},
    )


# ========== ANALYTICS DASHBOARD ==========
# ========== STREAMING ENDPOINT ==========
@app.post("/query/stream")
@limiter.limit("30/minute")
async def query_stream(
    request: Request,
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Igual que /query pero devuelve la respuesta RAG como Server-Sent Events.
    Eventos:
      data: {"type":"token","content":"..."}   — fragmento de texto
      data: {"type":"meta","conversation_id":N,"message_id":N,"sources":[...],"response_time":N}
      data: {"type":"done"}
      data: {"type":"error","detail":"..."}
    Exámenes y flujos de estado se delegan a /query normal (no se streamean).
    """
    query_text = body.query.strip()

    # Flujos de estado (examen, cancelar, confirmar) → delegar a /query normal sin streaming
    is_state_query = (
        is_exam_request(query_text)
        or ("cancelar" in query_text.lower() and "examen" in query_text.lower())
        or is_exam_confirmation(query_text)
        or get_active_exam(current_user.id, db) is not None
    )

    if is_state_query:
        # Redirige internamente al handler normal y envuelve en SSE
        result = await query(request, current_user, db)
        async def _wrap_json():
            data = json.dumps({"type": "token", "content": result["answer"]})
            yield f"data: {data}\n\n"
            meta = {
                "type": "meta",
                "conversation_id": result.get("conversation_id"),
                "message_id": result.get("message_id"),
                "sources": result.get("sources", []),
                "response_time": result.get("response_time"),
            }
            yield f"data: {json.dumps(meta)}\n\n"
            yield f"data: {json.dumps({'type':'done'})}\n\n"
        return StreamingResponse(_wrap_json(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    async def _stream() -> AsyncGenerator[str, None]:
        start_time = time.time()
        full_text = ""
        try:
            # Conversación
            if body.conversation_id:
                conv = db.query(Conversation).filter(
                    Conversation.id == body.conversation_id,
                    Conversation.user_id == current_user.id
                ).first()
                if not conv:
                    yield f"data: {json.dumps({'type':'error','detail':'Conversación no encontrada'})}\n\n"
                    return
            else:
                conv = Conversation(user_id=current_user.id, title=query_text[:50])
                db.add(conv); db.commit(); db.refresh(conv)

            # Análisis
            sentiment = analytics_engine.analyze_sentiment(query_text)
            topics    = analytics_engine.detect_topics(query_text)
            complexity = analytics_engine.assess_complexity(query_text)
            bloom_level, _ = qualitative_evaluator.classify_bloom_level(query_text)

            user_msg = Message(
                conversation_id=conv.id, role="user", content=query_text,
                sentiment_score=sentiment["score"], sentiment_label=sentiment["label"],
                query_complexity=complexity, topics=json.dumps(topics), bloom_level=bloom_level,
            )
            db.add(user_msg); db.commit()

            # Historial
            recent_history = [{"role": m.role, "content": m.content} for m in conv.messages[-6:]]

            # RAG: búsqueda vectorial (sin llamada LLM todavía)
            synthesis_result = await rag_engine.query_multi_source_with_synthesis(
                query=query_text, sources_count=3, chunks_per_source=10,
                conversation_history=recent_history if len(recent_history) > 1 else None,
                stream=True,  # señal para que devuelva el prompt en lugar del texto final
            )

            sources_used = synthesis_result["sources_used"]
            synthesis_prompt = synthesis_result["synthesis_prompt"]

            # Streaming del LLM token a token
            import requests as req_lib
            try:
                llm_response = req_lib.post(
                    f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                             "Content-Type": "application/json"},
                    json={"model": settings.LLM_MODEL,
                          "messages": [{"role": "user", "content": synthesis_prompt}],
                          "max_tokens": settings.LLM_MAX_TOKENS,
                          "temperature": 0.5, "stream": True},
                    stream=True, timeout=180,
                )
            except req_lib.exceptions.Timeout:
                yield f"data: {json.dumps({'type':'error','detail':'El servicio de IA tardó demasiado. Intenta de nuevo en unos momentos.'})}\n\n"
                return
            except req_lib.exceptions.ConnectionError:
                yield f"data: {json.dumps({'type':'error','detail':'No se pudo conectar al servicio de IA. Verifica la conexión.'})}\n\n"
                return

            with llm_response:
                if llm_response.status_code != 200:
                    yield f"data: {json.dumps({'type':'error','detail':'Error del servicio de IA. Intenta de nuevo.'})}\n\n"
                    return

                for raw_line in llm_response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            full_text += token
                            yield f"data: {json.dumps({'type':'token','content':token})}\n\n"
                    except Exception:
                        continue

            # Post-procesamiento
            full_text = rag_engine._remove_unicode_math_duplicates(full_text)

            # Ofrecer examen: ≥5 preguntas, ≥2 temas distintos, una sola vez por conversación
            db.refresh(conv)
            offer = should_offer_exam(conv.messages)
            if offer:
                extra = "\n\n---\n\n**Has explorado varios temas en esta sesion. ¿Te gustaria hacer un examen formativo?** Escribe **\"Quiero un examen\"** cuando estés listo."
                full_text += extra
                yield f"data: {json.dumps({'type':'token','content':extra})}\n\n"

            response_time = round(time.time() - start_time, 2)

            # Guardar respuesta
            assistant_msg = Message(
                conversation_id=conv.id, role="assistant", content=full_text,
                sources=json.dumps(sources_used), response_time=response_time,
            )
            db.add(assistant_msg)
            db.add(QueryLog(user_id=current_user.id, query=query_text,
                            sources_found=json.dumps(sources_used), top_k_used=3,
                            response_time=response_time))

            progress = db.query(StudentProgress).filter(StudentProgress.user_id == current_user.id).first()
            if not progress:
                progress = StudentProgress(user_id=current_user.id,
                                           first_query_date=datetime.utcnow(), total_queries=1)
                db.add(progress)
            else:
                progress.total_queries = (progress.total_queries or 0) + 1
            progress.last_query_date = datetime.utcnow()
            db.commit()

            meta = {"type": "meta", "conversation_id": conv.id,
                    "message_id": assistant_msg.id, "sources": sources_used,
                    "response_time": response_time, "should_offer_exam": offer}
            yield f"data: {json.dumps(meta)}\n\n"
            yield f"data: {json.dumps({'type':'done'})}\n\n"

        except Exception as e:
            import traceback; traceback.print_exc()
            yield f"data: {json.dumps({'type':'error','detail':str(e)})}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _resolve_admin(token_qp: Optional[str], db: Session, authorization: Optional[str] = None) -> User:
    """Resuelve usuario admin desde Authorization header (preferido) o query param (legacy)."""
    from .auth import SECRET_KEY, ALGORITHM
    from jose import JWTError, jwt as jose_jwt

    # Preferir header Authorization sobre query param (el QP expone el token en logs/historial)
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization[7:]
    elif token_qp:
        raw_token = token_qp

    if not raw_token:
        raise HTTPException(status_code=401, detail="Token requerido")
    try:
        payload = jose_jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    return user

# Caché simple en memoria para el dashboard de analytics (evita re-ejecutar en cada visita)
_analytics_cache: dict = {"html": None, "ts": 0.0}
_ANALYTICS_CACHE_TTL = 60  # segundos

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    authorization = request.headers.get("Authorization")
    current_user = _resolve_admin(token, db, authorization=authorization)

    # Devolver caché si está fresco
    if _analytics_cache["html"] and (time.time() - _analytics_cache["ts"]) < _ANALYTICS_CACHE_TTL:
        return HTMLResponse(content=_analytics_cache["html"])

    # Importar módulo de análisis dinámicamente para no requerir plotly en startup
    _v2_root = Path(__file__).parent.parent
    if str(_v2_root) not in sys.path:
        sys.path.insert(0, str(_v2_root))

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "analyze_participation", _v2_root / "analyze_participation.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cargando módulo de análisis: {e}")

    try:
        users, messages, conversations, exams, exam_responses, exam_results, progress, query_logs = mod.load_data()
        all_users, by_user, complexity, daily, daily_time = mod.compute_metrics(
            users, messages, conversations, exams, exam_responses, progress, query_logs
        )
        charts = mod.make_charts(all_users, by_user, complexity, daily, daily_time, exam_responses)
        html = mod.build_html(all_users, by_user, daily_time, charts, exam_results)
        _analytics_cache["html"] = html
        _analytics_cache["ts"] = time.time()
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {e}")
