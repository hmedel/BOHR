from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import timedelta
import json

from .rag_engine import RAGEngine
from .config import settings
from .database import get_db, User, Conversation, Message
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="RAG API con Autenticación", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG Engine
rag_engine = RAGEngine()

# ========== MODELOS ==========
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class QueryRequest(BaseModel):
    query: str
    conversation_id: int = None
    top_k: int = 1
    max_context: int = 500

class QueryResponse(BaseModel):
    answer: str
    sources: list
    context_used: str
    conversation_id: int

# ========== AUTH ENDPOINTS ==========
@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Registrar nuevo usuario"""
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Usuario creado exitosamente", "username": new_user.username}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login y obtener token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Obtener info del usuario actual"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }

# ========== RAG ENDPOINTS ==========
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "RAG API v2.0"}

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload documento (solo usuarios autenticados)"""
    try:
        file_path = f"data/uploads/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        doc_id = await rag_engine.process_document(file_path, file.filename)
        
        return {
            "status": "success",
            "filename": file.filename,
            "doc_id": doc_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Query con historial"""
    try:
        # Obtener o crear conversación
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversación no encontrada")
        else:
            # Crear nueva conversación
            conversation = Conversation(
                user_id=current_user.id,
                title=request.query[:50] + "..."
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Guardar mensaje del usuario
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.query
        )
        db.add(user_message)
        
        # Obtener respuesta del RAG
        result = await rag_engine.query(
            query=request.query,
            top_k=request.top_k,
            max_context=request.max_context
        )
        
        # Guardar respuesta del asistente
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            sources=json.dumps(result["sources"]),
            context_used=result["context_used"]
        )
        db.add(assistant_message)
        db.commit()
        
        return {
            **result,
            "conversation_id": conversation.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener conversaciones del usuario"""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()
    
    return [
        {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": len(conv.messages)
        }
        for conv in conversations
    ]

@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener mensajes de una conversación"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    messages = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": json.loads(msg.sources) if msg.sources else [],
            "created_at": msg.created_at
        }
        for msg in conversation.messages
    ]
    
    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": messages
    }

@app.get("/documents")
async def list_documents(current_user: User = Depends(get_current_user)):
    """Lista documentos"""
    docs = await rag_engine.list_documents()
    return {"documents": docs}

@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user)
):
    """Elimina documento"""
    await rag_engine.delete_document(doc_id)
    return {"status": "success"}
