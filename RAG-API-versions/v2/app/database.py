from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./data/rag_system.db"
os.makedirs("./data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("QueryLog", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("StudentProgress", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="Nueva conversación")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(String, index=True)
    content = Column(Text)
    sources = Column(Text)
    context_used = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Analytics
    feedback = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)
    
    # Análisis de sentimiento
    sentiment_score = Column(Float, nullable=True)  # -1 a 1
    sentiment_label = Column(String, nullable=True)  # positive, negative, neutral
    
    # Métricas de complejidad
    query_complexity = Column(String, nullable=True)  # basic, intermediate, advanced
    topics = Column(Text, nullable=True)  # JSON list de temas detectados

    # Bloom taxonomy and SOLO taxonomy fields
    bloom_level = Column(String, nullable=True, index=True)
    bloom_description = Column(Text, nullable=True)
    solo_level = Column(String, nullable=True)
    solo_characteristics = Column(JSON, nullable=True)
    qualitative_feedback = Column(Text, nullable=True)

    # Trazabilidad de la clasificación (P1.2)
    # JSON con: classifier_version, model_version, prompt_version, classified_at
    # Permite asociar cada bloom_level a la versión exacta del clasificador.
    classifier_meta = Column(JSON, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(Text)
    sources_found = Column(Text)
    top_k_used = Column(Integer)
    response_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="queries")

class StudentProgress(Base):
    """Tracking de progreso del estudiante"""
    __tablename__ = "student_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Métricas generales
    total_queries = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    avg_session_duration = Column(Float, default=0.0)
    
    # Métricas de engagement
    positive_feedback_count = Column(Integer, default=0)
    negative_feedback_count = Column(Integer, default=0)
    satisfaction_rate = Column(Float, default=0.0)
    
    # Métricas de aprendizaje
    topics_explored = Column(Text, nullable=True)  # JSON
    complexity_distribution = Column(Text, nullable=True)  # JSON
    avg_sentiment = Column(Float, default=0.0)
    bloom_distribution = Column(JSON, nullable=True)  # Added for main.py compatibility
    solo_distribution = Column(JSON, nullable=True)  # Added for main.py compatibility
    
    # Progreso temporal
    first_query_date = Column(DateTime, nullable=True)
    last_query_date = Column(DateTime, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="progress")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="Examen Formativo")
    exam_data = Column(JSON)  # Changed from 'questions' to 'exam_data' to match main.py usage
    exam_type = Column(String, default="formative")
    status = Column(String, default="active")
    topics_covered = Column(JSON)
    total_questions = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    responses = relationship("ExamResponse", back_populates="exam")
    results = relationship("ExamResult", back_populates="exam")

class ExamResponse(Base):
    __tablename__ = "exam_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    question_number = Column(Integer)
    student_answer = Column(Text)
    bloom_level = Column(String, nullable=True)
    solo_level = Column(String, nullable=True)
    evaluation_data = Column(JSON)
    
    # Análisis de sentimiento en respuestas de examen
    sentiment_score = Column(Float, nullable=True)  # -1 a 1
    sentiment_label = Column(String, nullable=True)  # positive, negative, neutral
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    exam = relationship("Exam", back_populates="responses")

class ExamResult(Base):
    __tablename__ = "exam_results"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    predominant_solo_level = Column(String, nullable=True)
    overall_description = Column(Text)
    strengths = Column(JSON)
    improvement_plan = Column(JSON)
    bloom_distribution = Column(JSON)
    solo_distribution = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    exam = relationship("Exam", back_populates="results")
