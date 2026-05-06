# Documentacion Tecnica - BOHR RAG v2

Documentacion de arquitectura, decisiones de diseno, diagramas de flujo y detalles de implementacion.

---

## 1. Arquitectura General

```
                         Internet
                            │
                    ┌───────┴───────┐
                    │  Cloudflare   │
                    │  Tunnel       │
                    │               │
                    │ chat.→:9000   │
                    │ api. →:8000   │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 │
  ┌──────────────┐  ┌──────────────┐          │
  │  Frontend    │  │  Backend     │          │
  │  :9000       │  │  :8000       │          │
  │              │  │              │          │
  │ index.html   │  │ FastAPI      │          │
  │ config.js    │  │ 12 workers   │          │
  │              │  │ Uvicorn      │          │
  │ Marked.js    │  │              │          │
  │ KaTeX 0.16.9 │  │ ┌──────────┐│          │
  │ Highlight.js │  │ │main.py   ││          │
  │              │  │ │(router)  ││          │
  │ Vanilla JS   │  │ └────┬─────┘│          │
  │ SPA          │  │      │      │          │
  └──────────────┘  │ ┌────┼────┐ │          │
                    │ │    │    │ │          │
                    │ ▼    ▼    ▼ │          │
                    │┌───┐┌──┐┌──┐│          │
                    ││RAG││Ex││An││          │
                    ││Eng││am││al││          │
                    ││   ││En││yt││          │
                    ││   ││g ││ic││          │
                    │└─┬─┘└──┘└──┘│          │
                    │  │   │   │  │          │
                    │  │ ┌─┴─┐ │  │          │
                    │  │ │Qua│ │  │          │
                    │  │ │lEv│ │  │          │
                    │  │ └───┘ │  │          │
                    │  │       │  │          │
                    │ ┌┴──┐┌───┴┐ │          │
                    │ │Aut││DB  │ │          │
                    │ │h  ││ORM │ │          │
                    │ └───┘└────┘ │          │
                    └──┬──┬──┬────┘          │
                       │  │  │              │
               ┌───────┘  │  └───────┐      │
               ▼          ▼          ▼      │
         ┌──────────┐┌──────────┐┌────────┐ │
         │ Ollama   ││ ChromaDB ││ SQLite │ │
         │ :11434   ││ (disco)  ││ (disco)│ │
         │          ││          ││        │ │
         │ nomic-   ││ 11,812   ││ 8 tablas││
         │ embed-   ││ chunks   ││        │ │
         │ text     ││ 7 libros ││        │ │
         └──────────┘└──────────┘└────────┘ │
                                            │
              ┌─────────────────────────────┘
              ▼
        ┌──────────┐
        │ DeepSeek │
        │ API      │
        │ deepseek │
        │ -chat    │
        │          │
        │ 4K max   │
        │ tokens   │
        └──────────┘
```

## 2. Componentes del Backend

### 2.1 main.py - Router y Estado de Examenes

**Responsabilidades:**
- Definicion de endpoints FastAPI
- Maquina de estados del sistema de examenes
- Orquestacion de motores (RAG, Exam, Analytics, Evaluator)
- Persistencia de mensajes y progreso

**Maquina de estados del query:**
```
                    POST /query
                        │
                ┌───────┴───────┐
                │ is_exam_      │
                │ request()?    │
                └───┬───────┬───┘
                   SI      NO
                    │       │
              ┌─────┘       │
              ▼             │
        ┌───────────┐       │
        │has active  │      │
        │exam?       │      │
        └──┬─────┬──┘      │
          SI    NO          │
           │     │          │
           │  ┌──┘          │
           │  ▼             │
           │ offer_exam()   │
           │  or            │
           │ "not ready"    │
           │                │
           │         ┌──────┘
           │         │
           │    ┌────┴────┐
           │    │"cancelar│
           │    │examen"? │
           │    └─┬────┬──┘
           │     SI   NO
           │      │    │
           │      │    ├──── is_exam_confirmation()? → Create exam + Q1
           │      │    │
           │      │    ├──── has active exam? → Evaluate answer
           │      │    │                        → Next Q or Summary
           │      │    │
           │      │    └──── Normal RAG flow
           │      │
           │      └──── Cancel exam
           │
           └──── "Ya tienes examen en progreso"
```

### 2.2 rag_engine.py - Pipeline RAG

**Metodo principal: `query_multi_source_with_synthesis()`**

```
query_multi_source_with_synthesis(query, sources_count=3, chunks_per_source=10)
    │
    ├── 1. Obtener lista de documentos disponibles (7)
    │
    ├── 2. Para CADA documento:
    │       similarity_search(query, k=50, filter={source: doc})
    │       Limitar a chunks_per_source (10)
    │       Almacenar resultados por fuente
    │
    ├── 3. Scoring de fuentes:
    │       score = len(chunks) × avg(position_weights)
    │       Ordenar por score descendente
    │
    ├── 4. Seleccionar top N fuentes (3)
    │       Combinar chunks de cada fuente
    │       ~30 chunks total, ~9,000 tokens
    │
    ├── 5. Construir prompt de sintesis:
    │       - Rol: tutor experto
    │       - Reglas LaTeX estrictas
    │       - Estructura: respuesta directa → explicacion → contexto
    │       - Ejemplos positivos y negativos
    │
    ├── 6. Llamar DeepSeek API:
    │       model: deepseek-chat
    │       max_tokens: 4000
    │       temperature: 0.4 (sintesis) o 0.3 (examenes)
    │       timeout: 120s
    │
    └── 7. Post-procesamiento:
            _remove_unicode_math_duplicates()
            - Fix $→$$ para multilinea
            - Proteger LaTeX existente
            - Eliminar Unicode math fuera de delimitadores
            - Restaurar LaTeX
```

**Post-procesamiento de Unicode Math:**

```
Input: "El hamiltoniano ∑ᵢ(-ℏ²/2m)∇²ᵢ describe..."
                         ▲ Unicode math ▲

Paso 1: Proteger LaTeX existente ($...$, $$...$$) con placeholders
Paso 2: Detectar expresiones Unicode math con regex
Paso 3: Si linea >60% math → eliminar linea completa
         Si linea tiene texto + math inline → eliminar solo la expresion math
Paso 4: Restaurar placeholders LaTeX

Output: "El hamiltoniano describe..."
        (la ecuacion ya esta en $$ mas arriba)
```

### 2.3 exam_engine.py - Sistema de Examenes

**Flujo del examen:**

```
should_offer_exam()
    ├── Requiere ≥3 queries del usuario
    └── Requiere ≥2 temas diferentes

generate_single_question_prompt()
    ├── Extrae conceptos de conversaciones previas
    ├── Nivel Bloom progresivo:
    │     Q1: comprender
    │     Q2-Q3: aplicar
    │     Q4-Q5: analizar
    ├── Evita repetir niveles
    └── Genera prompt JSON para DeepSeek

parse_question_from_llm()
    ├── Extrae JSON de respuesta (maneja markdown code blocks)
    └── Retorna: numero, nivel_bloom, tipo, enunciado, opciones, _respuesta_correcta

evaluate_answer()
    ├── Compara letra seleccionada vs correcta
    ├── Genera feedback SIN revelar respuesta correcta
    └── Retorna: is_correct, nivel, feedback, recursos

generate_final_summary()
    ├── Cuenta correctas/incorrectas
    ├── Distribucion Bloom
    ├── Nivel global: Excelente → Iniciando
    └── Plan de accion personalizado
```

### 2.4 analytics_engine.py - Analisis

| Metodo | Input | Output | Tecnica |
|---|---|---|---|
| `analyze_sentiment()` | texto | score, label, subjectivity | TextBlob polarity |
| `detect_topics()` | texto | lista de temas | Keyword matching (5 categorias) |
| `assess_complexity()` | texto | basic/intermediate/advanced | Keyword matching |
| `calculate_progress_metrics()` | mensajes | metricas agregadas | Agregacion estadistica |

**Categorias de temas:**
- estructura_atomica: atomo, orbital, electron, proton, neutron, nucleo
- mecanica_cuantica: cuantico, onda, particula, heisenberg, schrodinger, hamiltoniano
- enlaces_quimicos: enlace, ionico, covalente, metalico, molecular
- espectroscopia: espectro, foton, emision, absorcion, energia
- orbitales: orbital, s, p, d, f, hibridacion

### 2.5 qualitative_evaluator.py - Bloom/SOLO

**Taxonomia de Bloom (6 niveles, keywords por nivel):**

```
Recordar ← define, lista, enumera, nombra
    ↓
Comprender ← explica, por que, como, diferencia, compara
    ↓
Aplicar ← calcula, resuelve, usa, aplica, demuestra
    ↓
Analizar ← analiza, examina, distingue, relaciona
    ↓
Evaluar ← evalua, critica, juzga, argumenta
    ↓
Crear ← disena, crea, propone, inventa, desarrolla
```

**Modelo SOLO (5 niveles, indicadores):**

```
Preestructural ← "no se", "no entiendo", respuesta irrelevante
    ↓
Uniestructural ← respuesta corta (<40 palabras), sin conexiones
    ↓
Multiestructural ← multiples ideas independientes, tipo lista
    ↓
Relacional ← conectores causales ("porque", "debido a"), ≥50 palabras
    ↓
Abstracto Extendido ← generaliza, abstrae, propone hipotesis
```

**Mapeo Bloom→SOLO esperado:**
- recordar → uniestructural
- comprender → multiestructural
- aplicar/analizar → relacional
- evaluar/crear → abstracto_extendido

## 3. Frontend

### 3.1 Pipeline de Renderizado LaTeX

```
Contenido del backend (string)
    │
    ▼
renderContentWithLatex(content)
    │
    ├── 1. Normalizar backslashes: \\( → \(
    │
    ├── 2. Proteger LaTeX con placeholders:
    │       $$...$$  → %%LATEX_DISPLAY_0%%
    │       \[...\]  → %%LATEX_DISPLAY_1%%
    │       $...$    → %%LATEX_INLINE_2%%
    │       \(...\)  → %%LATEX_INLINE_3%%
    │
    ├── 3. marked.parse() → Markdown a HTML
    │       (sin tocar el LaTeX protegido)
    │
    └── 4. Restaurar placeholders → LaTeX original en HTML
            │
            ▼
    innerHTML = resultado
            │
            ▼
    applyKatexToElement(element)
    │
    └── renderMathInElement(element, {
            delimiters: [$$, $, \[\], \(\)],
            throwOnError: false,
            strict: false,
            trust: true
        })
```

**Por que es necesario proteger LaTeX:**
- Marked.js interpreta `_` como italic: `$\alpha_1$` → `$\alpha<em>1$`
- Marked.js interpreta `*` como bold: `$a * b$` → `$a <strong> b$`
- Marked.js puede envolver `$...$` en `<p>` o `<code>` tags

### 3.2 Estructura de la SPA

```
index.html (~1100 lineas)
    │
    ├── <head>
    │     ├── Marked.js CDN
    │     ├── Highlight.js CDN + github-dark theme
    │     └── KaTeX 0.16.9 (CSS + JS + auto-render, defer)
    │
    ├── <style> (~550 lineas)
    │     ├── Variables CSS (--unam-azul, --unam-oro, etc.)
    │     ├── Auth screen (login/register forms)
    │     ├── App layout (header, sidebar, chat, input)
    │     ├── Message styles (user/assistant, markdown, code)
    │     └── KaTeX styles (display, inline, scrollbar, errors)
    │
    ├── Auth Screen
    │     ├── Login form → handleLogin() → POST /token
    │     └── Register form → handleRegister() → POST /register
    │
    ├── App Screen
    │     ├── Header (titulo, analytics btn, logout)
    │     ├── Sidebar (new chat btn, conversations list)
    │     ├── Chat container (messages + input area)
    │     └── Input (textarea + send button)
    │
    └── <script> (~450 lineas)
          ├── State: currentUser, currentConversationId, accessToken
          ├── Marked config (breaks, gfm, highlight)
          ├── renderContentWithLatex() ← pipeline LaTeX
          ├── applyKatexToElement() ← KaTeX post-DOM
          ├── Auth functions (login, register, logout)
          ├── showApp() → loadConversations()
          ├── loadConversation(id) → render messages
          ├── sendMessage() → POST /query → addMessage()
          ├── addMessage() → render + applyKatex
          ├── submitFeedback() → POST /feedback
          └── localStorage persistence (token, user)
```

### 3.3 Deteccion de Entorno (config.js)

```javascript
isDevelopment = hostname === 'localhost' ||
                hostname === '132.248.102.133' ||
                port === '9000'

API_URL = isDevelopment
    ? 'http://132.248.102.133:8000'     // Desarrollo
    : 'https://api.bohrbot.space'        // Produccion
```

## 4. Base de Datos

### 4.1 Diagrama ER

```
┌──────────┐     ┌───────────────┐     ┌──────────┐
│  users   │────<│ conversations │────<│ messages │
│          │     │               │     │          │
│ id       │     │ id            │     │ id       │
│ username │     │ user_id (FK)  │     │ conv_id  │
│ email    │     │ title         │     │ role     │
│ password │     │ created_at    │     │ content  │
│ full_name│     │ updated_at    │     │ sources  │
│ is_admin │     └───────────────┘     │ sentiment│
│ created  │                           │ bloom    │
└────┬─────┘                           │ solo     │
     │                                 │ feedback │
     │                                 │ resp_time│
     │                                 └──────────┘
     │
     ├────<┌────────────┐
     │     │ query_logs │
     │     │ id, query  │
     │     │ sources    │
     │     │ resp_time  │
     │     └────────────┘
     │
     ├────<┌──────────────────┐
     │     │ student_progress │
     │     │ total_queries    │
     │     │ topics_explored  │
     │     │ complexity_dist  │
     │     │ first/last_query │
     │     └──────────────────┘
     │
     └────<┌─────────┐     ┌────────────────┐     ┌──────────────┐
           │ exams   │────<│ exam_responses │     │ exam_results │
           │         │     │                │     │              │
           │ id      │     │ id             │     │ id           │
           │ user_id │     │ exam_id (FK)   │     │ exam_id (FK) │
           │ title   │     │ question_num   │     │ solo_level   │
           │ exam_dat│     │ student_answer │     │ strengths    │
           │ topics  │     │ bloom_level    │     │ improvement  │
           │ total_q │     │ solo_level     │     │ bloom_dist   │
           │ status  │     │ evaluation     │     │ solo_dist    │
           └─────────┘     │ sentiment      │     └──────────────┘
                           └────────────────┘
```

### 4.2 Campos de Analytics en Messages

Cada mensaje del usuario almacena:
- `sentiment_score`: -1.0 a 1.0 (TextBlob polarity)
- `sentiment_label`: positive, negative, neutral
- `query_complexity`: basic, intermediate, advanced
- `topics`: JSON array de temas detectados
- `bloom_level`: nivel taxonomia de Bloom
- `solo_level`: nivel modelo SOLO

## 5. Decisiones de Diseno

### Por que SHA256 en vez de bcrypt?
bcrypt tiene limite de 72 bytes. Algunos passwords (como emails largos usados como password) exceden ese limite. SHA256 no tiene esa restriccion. Para un sistema educativo interno, la seguridad es suficiente.

### Por que ChromaDB con busqueda por fuente separada?
ChromaDB no garantiza diversidad de fuentes en una busqueda global. Buscar en cada documento por separado y luego rankear asegura que las respuestas provengan de multiples libros, no solo del que tiene mas chunks similares.

### Por que DeepSeek y no OpenAI?
Costo. DeepSeek ofrece calidad similar a GPT-4 para texto academico en espanol a una fraccion del precio. El sistema esta disenado para ser facilmente switcheable (cambiar LLM_MODEL y DEEPSEEK_BASE_URL en .env).

### Por que Ollama local para embeddings?
Los embeddings se ejecutan en cada busqueda (7 docs × 1 embedding por query). Usar un API externo seria lento y costoso. Ollama con nomic-embed-text corre localmente sin costo y con baja latencia.

### Por que vanilla JS y no React/Vue?
El frontend es un unico archivo HTML servido por un HTTP server de Python. No requiere build step, no requiere Node.js, y es trivial de desplegar. Para un SPA educativo con ~1100 lineas, un framework seria overengineering.

### Por que max_tokens = 4000?
Con 1500 tokens, las ecuaciones largas (hamiltoniano multielectronico, ecuaciones de Maxwell) se truncaban a mitad de la expresion LaTeX. 4000 permite ecuaciones completas + explicacion detallada sin truncamiento.

### Por que 10 chunks por fuente en vez de 20?
20 chunks × 3 fuentes = 60 chunks (~18K tokens de contexto). Mucho contexto diluye la relevancia y aumenta el tiempo de respuesta. 10 chunks × 3 fuentes = 30 chunks (~9K tokens) da respuestas igual de completas en ~40s vs ~60s.

## 6. Dependencias

### Python (requirements.txt)

| Paquete | Version | Proposito |
|---|---|---|
| fastapi | latest | Framework web |
| uvicorn[standard] | latest | ASGI server |
| langchain | latest | Orquestacion RAG |
| langchain-community | latest | ChromaDB integration |
| langchain-ollama | latest | Ollama embeddings |
| chromadb | latest | Vector database |
| pypdf | latest | Lectura de PDFs |
| python-multipart | latest | Upload de archivos |
| requests | latest | Llamadas a DeepSeek API |
| pydantic | latest | Validacion de datos |
| pydantic-settings | latest | Configuracion desde .env |
| aiofiles | latest | Archivos async |
| python-dotenv | latest | Variables de entorno |
| python-jose[cryptography] | latest | JWT tokens |
| passlib[bcrypt] | latest | (legacy, no se usa) |
| textblob | latest | Analisis de sentimiento |
| sqlalchemy | latest | ORM para SQLite |

### Frontend (CDN)

| Libreria | Version | Proposito |
|---|---|---|
| KaTeX | 0.16.9 | Renderizado de LaTeX |
| Marked.js | latest | Markdown a HTML |
| Highlight.js | 11.9.0 | Syntax highlighting |
