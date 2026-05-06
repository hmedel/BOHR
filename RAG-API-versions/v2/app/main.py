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
from .config import settings
from .database import get_db, User, Conversation, Message, QueryLog, StudentProgress, Exam, ExamResponse, ExamResult
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from .analytics_engine import AnalyticsEngine
from .qualitative_evaluator import QualitativeEvaluator
from .exam_engine import ExamEngine

app = FastAPI(title="Asistente de Estructura de la Materia", version="2.7")

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
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

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
    """Obtener examen activo (sin completar) del usuario"""
    # Buscar último examen
    latest_exam = db.query(Exam).filter(
        Exam.user_id == user_id
    ).order_by(Exam.created_at.desc()).first()
    
    if not latest_exam:
        return None
    
    # Verificar si está completo
    exam_data = json.loads(latest_exam.exam_data)
    total_q = exam_data.get("total_questions", 3)
    
    responses_count = db.query(ExamResponse).filter(
        ExamResponse.exam_id == latest_exam.id
    ).count()
    
    # Si ya está completo, no es "activo"
    if responses_count >= total_q:
        return None
    
    return latest_exam

# ========== MAIN QUERY ENDPOINT ==========
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.7"}

@app.post("/query")
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    
    try:
        query_text = request.query.strip()
        
        # ===== 1. DETECTAR SOLICITUD DE EXAMEN =====
        if is_exam_request(query_text):
            # Verificar si ya tiene un examen activo
            active_exam = get_active_exam(current_user.id, db)
            
            if active_exam:
                exam_data = json.loads(active_exam.exam_data)
                current_q = exam_data.get("current_question", 1)
                total_q = exam_data.get("total_questions", 3)
                
                return {
                    "answer": f"""⚠️ **Ya tienes un examen en progreso**

Estás en la pregunta {current_q} de {total_q}.

**Opciones:**
1. Continúa respondiendo la pregunta actual
2. Si quieres cancelar este examen y empezar uno nuevo, escribe: **"Cancelar examen actual"**
""",
                    "sources": []
                }
            
            # Verificar si está listo para un examen
            conv = None
            if request.conversation_id:
                conv = db.query(Conversation).filter(
                    Conversation.id == request.conversation_id,
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
                    "answer": f"""📚 **Aún no estás listo para un nuevo examen**

{exam_check['reason']}

Continúa estudiando y luego podrás tomar un examen formativo.""",
                    "sources": []
                }
            else:
                return {
                    "answer": f"""🎓 **¡Estás listo para un examen formativo!**

**Resumen:**
- ✅ Consultas realizadas: {exam_check['queries_count']}
- ✅ Temas cubiertos: {', '.join(exam_check['topics_covered'][:3])}

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
                    "answer": """✅ **Examen cancelado**

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
            
            # Crear nuevo examen
            all_messages = db.query(Message).join(Conversation).filter(
                Conversation.user_id == current_user.id,
                Message.role == "user"
            ).all()
            
            topics = set()
            for msg in all_messages:
                if msg.topics:
                    try:
                        topics.update(json.loads(msg.topics))
                    except Exception:
                        logger.debug("topics JSON inválido en mensaje %s", msg.id)
            
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

            # Generar primera pregunta
            prompt = exam_engine.generate_single_question_prompt(
                conversation_history=all_messages,
                topics=list(topics),
                question_number=1,
                total_questions=total_questions,
                previous_levels=[],
                difficulty_profile=difficulty_profile,
            )
            
            question_json = rag_engine._call_llm(prompt, temperature=0.3)
            question = exam_engine.parse_question_from_llm(question_json)
            
            if not question:
                raise HTTPException(status_code=500, detail="Error generando pregunta")
            
            # Guardar pregunta
            exam_data = json.loads(new_exam.exam_data)
            exam_data["questions"] = [question]
            exam_data["question_1"] = question
            new_exam.exam_data = json.dumps(exam_data)
            db.commit()
            
            # Formatear pregunta
            question_display = f"""# 📝 Pregunta 1 de {total_questions}

**Nivel:** {question['nivel_bloom'].title()}

{question['enunciado']}

"""
            
            if question.get("tipo") == "opcion_multiple" and question.get("opciones"):
                for opcion in question['opciones']:
                    question_display += f"{opcion}\n"
                question_display += "\n**Responde con la letra (A, B, C o D) y justifica brevemente tu elección.**"
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
                
                # Guardar respuesta con análisis de sentimiento
                exam_response = ExamResponse(
                    exam_id=active_exam.id,
                    user_id=current_user.id,
                    question_number=current_q,
                    student_answer=query_text,
                    bloom_level=current_question.get("nivel_bloom", ""),
                    solo_level=evaluation.get("nivel", ""),
                    evaluation_data=json.dumps(evaluation),
                    sentiment_score=sentiment["score"],
                    sentiment_label=sentiment["label"]
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
                    
                    prompt = exam_engine.generate_single_question_prompt(
                        conversation_history=all_messages,
                        topics=exam_data.get("topics", []),
                        question_number=next_q,
                        total_questions=total_q,
                        previous_levels=previous_levels,
                        difficulty_profile=exam_data.get("difficulty_profile"),
                    )
                    
                    next_question_json = rag_engine._call_llm(prompt, temperature=0.3)
                    next_question = exam_engine.parse_question_from_llm(next_question_json)
                    
                    if next_question:
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

# 📝 Pregunta {next_q} de {total_q}

**Nivel:** {next_question['nivel_bloom'].title()}

{next_question['enunciado']}

"""
                        if next_question.get("tipo") == "opcion_multiple" and next_question.get("opciones"):
                            for opcion in next_question['opciones']:
                                feedback_display += f"{opcion}\n"
                            feedback_display += "\n**Responde con la letra y justifica brevemente.**"
                
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
                    
                    # Guardar resultado final
                    correct_count = sum(1 for qa in questions_and_answers if qa.get("evaluation", {}).get("is_correct", False))
                    
                    # Calcular distribuciones reales
                    bloom_dist = {}
                    solo_dist = {}
                    for qa in questions_and_answers:
                        bl = qa.get("question", {}).get("nivel_bloom", "")
                        sl = qa.get("evaluation", {}).get("nivel", "")
                        if bl: bloom_dist[bl] = bloom_dist.get(bl, 0) + 1
                        if sl: solo_dist[sl] = solo_dist.get(sl, 0) + 1

                    predominant_solo = max(solo_dist, key=solo_dist.get) if solo_dist else (
                        "relacional" if correct_count >= total_q * 0.7 else "multiestructural"
                    )
                    strengths = [f"Respondió correctamente {correct_count} de {total_q} preguntas"]
                    if bloom_dist:
                        top_bloom = max(bloom_dist, key=bloom_dist.get)
                        strengths.append(f"Mayor desempeño en nivel Bloom: {top_bloom}")

                    exam_result = ExamResult(
                        exam_id=active_exam.id,
                        user_id=current_user.id,
                        predominant_solo_level=predominant_solo,
                        overall_description=f"Completó {total_q} preguntas con {correct_count} correctas",
                        strengths=json.dumps(strengths),
                        improvement_plan=json.dumps({"plan": "Revisar los temas con menor desempeño"}),
                        bloom_distribution=json.dumps(bloom_dist),
                        solo_distribution=json.dumps(solo_dist),
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
        if request.conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
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
        bloom_level, _ = qualitative_evaluator.classify_bloom_level(query_text)

        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=query_text,
            sentiment_score=sentiment["score"],
            sentiment_label=sentiment["label"],
            query_complexity=complexity,
            topics=json.dumps(topics),
            bloom_level=bloom_level,
        )
        db.add(user_msg)
        db.commit()
        
        # Historial reciente de la conversación para contexto
        recent_history = []
        if conv.messages:
            for m in conv.messages[-6:]:
                recent_history.append({"role": m.role, "content": m.content})

        # RAG Multi-Source CON SÍNTESIS del LLM
        synthesis_result = await rag_engine.query_multi_source_with_synthesis(
            query=query_text,
            sources_count=3,
            chunks_per_source=10,
            conversation_history=recent_history if len(recent_history) > 1 else None,
        )
        
        response_time = time.time() - start_time
        
        # Usar respuesta sintetizada del LLM
        answer_display = synthesis_result["synthesized_answer"]
        
        # Verificar si debe ofrecer examen (después de 3 consultas)
        total_queries = len([m for m in conv.messages if m.role == "user"])
        should_offer = total_queries >= 3 and total_queries % 3 == 0
        
        if should_offer:
            answer_display += "\n\n---\n\n"
            answer_display += "💡 **Has realizado varias consultas. ¿Te gustaría hacer una evaluación de los temas que has visto?**\n\n"
            answer_display += "Escribe **\"Quiero un examen\"** si deseas evaluarte.\n\n"
        
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
        
        db.commit()
        
        return {
            "answer": answer_display,
            "sources": synthesis_result["sources_used"],
            "conversation_id": conv.id,
            "message_id": assistant_msg.id,
            "response_time": round(synthesis_result["response_time"], 2),
            "should_offer_exam": should_offer
        }
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# [Resto de endpoints sin cambios]
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == feedback.message_id).first()
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


# ========== ANALYTICS DASHBOARD ==========
# ========== STREAMING ENDPOINT ==========
@app.post("/query/stream")
async def query_stream(
    request: QueryRequest,
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
    query_text = request.query.strip()

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
            if request.conversation_id:
                conv = db.query(Conversation).filter(
                    Conversation.id == request.conversation_id,
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
            with req_lib.post(
                f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": settings.LLM_MODEL,
                      "messages": [{"role": "user", "content": synthesis_prompt}],
                      "max_tokens": settings.LLM_MAX_TOKENS,
                      "temperature": 0.5, "stream": True},
                stream=True, timeout=180,
            ) as llm_resp:
                if llm_resp.status_code != 200:
                    yield f"data: {json.dumps({'type':'error','detail':'Error LLM'})}\n\n"
                    return

                for raw_line in llm_resp.iter_lines():
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

            # Oferta de examen
            total_user_msgs = db.query(Message).filter(
                Message.conversation_id == conv.id, Message.role == "user"
            ).count()
            should_offer = total_user_msgs >= 3 and total_user_msgs % 3 == 0
            if should_offer:
                extra = "\n\n---\n\n💡 **¿Te gustaría hacer un examen sobre los temas que has visto?** Escribe **\"Quiero un examen\"**."
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
                    "response_time": response_time, "should_offer_exam": should_offer}
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


def _resolve_admin(token_qp: Optional[str], db: Session) -> User:
    from .auth import SECRET_KEY, ALGORITHM
    from jose import JWTError, jwt as jose_jwt
    if not token_qp:
        raise HTTPException(status_code=401, detail="Token requerido")
    try:
        payload = jose_jwt.decode(token_qp, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    return user

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    current_user = _resolve_admin(token, db)

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
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {e}")
