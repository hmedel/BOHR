# 🔬 RAG-API - Sistema de Asistencia Educativa en Química

Sistema de Retrieval-Augmented Generation (RAG) para educación en química y física, combinando embeddings locales (Ollama) con el modelo DeepSeek para respuestas contextualizadas.

## 🌟 Características

- 🔐 **Autenticación JWT** - Sistema multiusuario con tokens seguros
- 📚 **Vector Search** - ChromaDB para búsqueda semántica eficiente
- 🤖 **LLM Integrado** - DeepSeek API para respuestas inteligentes
- 💾 **Historial Persistente** - SQLite para conversaciones
- 🎨 **Interfaz Web** - UI responsiva con gradientes modernos
- 📊 **API RESTful** - FastAPI con documentación automática

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.8+
- [Ollama](https://ollama.ai) instalado y corriendo
- Cuenta en [DeepSeek](https://platform.deepseek.com)

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd RAG-API
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env y agregar tu DEEPSEEK_API_KEY
# Generar JWT_SECRET con: openssl rand -hex 32
```

3. **Ejecutar el script de inicio seguro**
```bash
chmod +x startup_secure.sh
./startup_secure.sh
```

El script automáticamente:
- ✅ Valida dependencias
- ✅ Configura el entorno virtual
- ✅ Instala paquetes necesarios
- ✅ Inicializa la base de datos
- ✅ Inicia backend y frontend
- ✅ Realiza health checks

## 📖 Uso

### Acceso a la Aplicación

- **Frontend**: http://localhost:9000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Registro y Autenticación

1. Registrar nuevo usuario:
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "secure123"}'
```

2. Obtener token:
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=secure123"
```

### Cargar Documentos

```bash
# Script automático para cargar libros
./load_books.sh

# O manualmente via API
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.md"
```

### Realizar Consultas

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Qué es un enlace iónico?",
    "top_k": 3,
    "max_context": 1000
  }'
```

## 🏗️ Arquitectura

```
RAG-API/
├── app/                    # Backend FastAPI
│   ├── main.py            # Endpoints principales
│   ├── rag_engine.py      # Motor RAG mejorado
│   ├── auth.py            # Autenticación JWT segura
│   ├── database.py        # Modelos SQLAlchemy
│   └── config.py          # Configuración con validación
├── data/
│   ├── chroma/            # Vector embeddings
│   ├── uploads/           # Documentos cargados
│   └── rag_system.db      # Base de datos SQLite
├── frontend/
│   └── index.html         # Interfaz web
└── logs/                  # Logs del sistema
```

## 🔧 Configuración

### Variables de Entorno (.env)

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `DEEPSEEK_API_KEY` | API key de DeepSeek | ✅ |
| `JWT_SECRET` | Secret para tokens JWT | ✅ |
| `OLLAMA_BASE_URL` | URL de Ollama | ✅ |
| `EMBEDDINGS_MODEL` | Modelo de embeddings | ✅ |
| `CHUNK_SIZE` | Tamaño de chunks | ❌ (default: 500) |
| `BATCH_SIZE` | Tamaño de batch | ❌ (default: 50) |

### Modelos Requeridos

```bash
# Instalar modelo de embeddings
ollama pull nomic-embed-text:latest
```

## 🔒 Seguridad

### ⚠️ Mejoras Implementadas

- ✅ **Credenciales removidas del código** - Ahora en variables de entorno
- ✅ **JWT Secret dinámico** - Generado criptográficamente
- ✅ **Validación de configuración** - Verificación al inicio
- ✅ **.gitignore actualizado** - Protección de archivos sensibles
- ✅ **Retry logic en LLM** - Manejo robusto de errores

### 🚨 Acciones Requeridas

1. **Regenerar API Keys**
   - Visitar [DeepSeek Platform](https://platform.deepseek.com)
   - Revocar keys anteriores
   - Generar nueva key

2. **Configurar JWT Secret**
```bash
# Generar secret seguro
openssl rand -hex 32
# Agregar a .env
```

3. **Nunca commitear .env**
```bash
# Verificar .gitignore
git status --ignored
```

## 📊 API Endpoints

### Autenticación
- `POST /register` - Registro de usuarios
- `POST /token` - Obtener JWT token
- `GET /users/me` - Info del usuario actual

### RAG Operations
- `POST /upload` - Cargar documento (requiere auth)
- `POST /query` - Consultar con RAG (requiere auth)
- `GET /conversations` - Listar conversaciones
- `GET /conversations/{id}` - Obtener mensajes
- `GET /documents` - Listar documentos
- `DELETE /documents/{id}` - Eliminar documento

## 🧪 Testing

```bash
# Test completo del sistema
./full_test.sh

# Test de health
curl http://localhost:8000/health

# Ver logs
tail -f logs/backend.log
tail -f logs/frontend.log
```

## 🐳 Docker

```bash
# Construir imagen
docker build -t rag-api .

# Ejecutar contenedor
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## 🛠️ Troubleshooting

### Ollama no conecta
```bash
# Verificar que Ollama esté corriendo
ollama serve
# Verificar modelo instalado
ollama list
```

### DeepSeek API errors
- Verificar saldo en cuenta
- Revisar rate limits
- Validar API key en .env

### Puerto en uso
```bash
# Liberar puertos
fuser -k 8000/tcp
fuser -k 9000/tcp
```

## 📈 Mejoras Futuras

- [ ] Frontend con React/Vue
- [ ] WebSocket para real-time
- [ ] Cache de embeddings
- [ ] Tests automatizados
- [ ] CI/CD pipeline
- [ ] Métricas y monitoring
- [ ] Rate limiting
- [ ] Multi-idioma

## 📝 Licencia

Este proyecto es para fines educativos.

## 👥 Contribución

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 🆘 Soporte

Para issues y preguntas, abrir un [Issue](https://github.com/your-repo/issues)

---

**⚠️ IMPORTANTE**: Este sistema contiene mejoras de seguridad críticas. Asegúrese de:
1. Nunca commitear archivos `.env`
2. Regenerar todas las API keys
3. Usar secrets seguros para JWT
4. Mantener Ollama actualizado