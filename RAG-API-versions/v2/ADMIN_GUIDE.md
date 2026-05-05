# Guia de Administracion - BOHR RAG v2

Guia practica para administrar el sistema BOHR RAG v2: gestion de usuarios, servicio, documentos, base de datos y monitoreo.

---

## 1. Gestion de Usuarios

### Dar de Alta un Alumno

```bash
curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"correo@gmail.com","email":"correo@gmail.com","password":"numeroDeCuenta","full_name":"Nombre Completo"}'
```

### Alta Masiva desde CSV

Si tienes un CSV con columnas `ESTUDIANTE,Email,Cuenta`:

```bash
while IFS=, read -r nombre email cuenta; do
  [ -z "$email" ] && continue
  curl -s -X POST http://localhost:8000/register \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$email\",\"email\":\"$email\",\"password\":\"$cuenta\",\"full_name\":\"$nombre\"}"
  echo ""
done < <(tail -n +2 alumnos.csv)
```

### Verificar Login de un Alumno

```bash
curl -s -X POST http://localhost:8000/token \
  -d "username=correo@gmail.com&password=contraseña"
```

### Listar Todos los Usuarios

```bash
sqlite3 -header -column data/rag_system.db \
  "SELECT id, username, email, full_name, is_admin, created_at FROM users ORDER BY id;"
```

### Buscar un Usuario

```bash
sqlite3 data/rag_system.db \
  "SELECT id, username, email, full_name FROM users WHERE email LIKE '%buscar%' OR full_name LIKE '%buscar%';"
```

### Cambiar Password

```bash
NEW_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('nuevoPassword'.encode()).hexdigest())")
sqlite3 data/rag_system.db \
  "UPDATE users SET hashed_password='$NEW_HASH' WHERE email='correo@gmail.com';"
```

### Hacer Admin

```bash
sqlite3 data/rag_system.db \
  "UPDATE users SET is_admin=1 WHERE email='correo@gmail.com';"
```

### Eliminar Usuario (cascada: borra todo su historial)

```bash
sqlite3 data/rag_system.db "DELETE FROM users WHERE email='correo@gmail.com';"
```

---

## 2. Gestion del Servicio

### Iniciar Todo (backend + frontend)

El entorno conda esta en `/home/medel/.julia/conda/3/x86_64/envs/bohrenv/`.
**Nota:** `conda activate` no funciona en subshells no-interactivos; usar ruta absoluta al Python.

```bash
PYTHON=/home/medel/.julia/conda/3/x86_64/envs/bohrenv/bin/python

# Backend (4 workers)
cd /home/medel/BOHR/RAG-API-versions/v2
$PYTHON -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --workers 4 --log-level info \
  >> logs/backend_production.log 2>&1 &
echo "Backend PID: $!"

# Frontend
cd frontend && nohup python -m http.server 9000 > frontend.log 2>&1 &
cd ..
```

O usar el script: `./deploy_production.sh`

### Reiniciar Solo el Backend

```bash
pkill -f "uvicorn app.main:app"
sleep 3
PYTHON=/home/medel/.julia/conda/3/x86_64/envs/bohrenv/bin/python
$PYTHON -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --workers 4 --log-level info \
  >> logs/backend_production.log 2>&1 &
```

### Detener Todo

```bash
pkill -f "uvicorn app.main:app"
pkill -f "http.server 9000"
```

### Verificar Estado

```bash
# Health check rapido
curl -s http://localhost:8000/health

# Procesos activos
ps aux | grep -E "uvicorn|http.server" | grep -v grep

# Puertos
ss -tlnp | grep -E "8000|9000"

# URLs publicas
curl -s -o /dev/null -w "%{http_code}" https://api.bohrbot.space/health
curl -s -o /dev/null -w "%{http_code}" https://chat.bohrbot.space

# Servicios externos
curl -s http://localhost:11434/api/tags  # Ollama
```

### Logs

```bash
tail -f logs/backend_production.log           # Backend en tiempo real
grep -i error logs/backend_production.log     # Solo errores
tail -f logs/cloudflare_tunnel.log            # Tunnel
```

---

## 3. Reporte de Participacion (Analytics)

### Dashboard web (solo admins)

Abrir en el navegador: `https://api.bohrbot.space/analytics?token=<JWT>`

O desde el chat: login como admin → botón **📊 Analytics** (esquina superior derecha).

### Generar reporte HTML + snapshots CSV

```bash
cd /home/medel/BOHR/RAG-API-versions/v2
PYTHON=/home/medel/.julia/conda/3/x86_64/envs/bohrenv/bin/python
$PYTHON analyze_participation.py
# Salida: analytics/reports/reporte_YYYYMMDD_HHMMSS.html
#         analytics/snapshots/snapshot_YYYYMMDD_HHMMSS/
```

### Estadisticas rapidas desde SQLite

```bash
sqlite3 -header -column data/rag_system.db "
SELECT 'Usuarios' as tabla, COUNT(*) as total FROM users
UNION ALL SELECT 'Conversaciones', COUNT(*) FROM conversations
UNION ALL SELECT 'Mensajes', COUNT(*) FROM messages
UNION ALL SELECT 'Examenes completados', COUNT(*) FROM exams WHERE status='completed'
UNION ALL SELECT 'Examenes activos', COUNT(*) FROM exams WHERE status='active'
UNION ALL SELECT 'Query logs', COUNT(*) FROM query_logs;
"
```

### Actividad por Usuario

```bash
sqlite3 -header -column data/rag_system.db "
SELECT u.full_name as nombre,
  (SELECT COUNT(*) FROM conversations c WHERE c.user_id = u.id) as chats,
  (SELECT COUNT(*) FROM messages m JOIN conversations c ON m.conversation_id = c.id
   WHERE c.user_id = u.id AND m.role='user') as preguntas,
  (SELECT COUNT(*) FROM exams e WHERE e.user_id = u.id AND e.status='completed') as examenes
FROM users u ORDER BY preguntas DESC;
"
```

### Tiempos de Respuesta

```bash
sqlite3 -header -column data/rag_system.db "
SELECT DATE(created_at) as fecha,
  COUNT(*) as consultas,
  ROUND(AVG(response_time),1) as prom_seg,
  ROUND(MAX(response_time),1) as max_seg
FROM query_logs
GROUP BY DATE(created_at)
ORDER BY fecha DESC LIMIT 10;
"
```

### Exportar Historial de un Alumno

```bash
sqlite3 -header -csv data/rag_system.db "
SELECT m.created_at, m.role, m.content, m.sentiment_label,
       m.query_complexity, m.bloom_level
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN users u ON c.user_id = u.id
WHERE u.email = 'correo@gmail.com'
ORDER BY m.created_at;
" > export_alumno.csv
```

### Limpiar Conversaciones Viejas

```bash
# Conversaciones de mas de 90 dias
sqlite3 data/rag_system.db \
  "DELETE FROM conversations WHERE created_at < datetime('now', '-90 days');"
```

---

## 4. Gestion de Documentos

### Ver Documentos Indexados

```bash
curl -s -H "Authorization: Bearer <TOKEN>" http://localhost:8000/documents | python3 -m json.tool
```

### Indexar un Libro Nuevo

1. Convertir PDF a markdown y colocar en `data/uploads/`
2. Indexar:

```bash
PYTHON=/home/medel/.julia/conda/3/x86_64/envs/bohrenv/bin/python
$PYTHON -c "
import asyncio
from app.rag_engine import RAGEngine
engine = RAGEngine()
asyncio.run(engine.process_document('data/uploads/NuevoLibro.md', 'NuevoLibro.md'))
"
```

3. Reiniciar backend para que detecte el nuevo documento

### Cargar Todos los Libros

```bash
./load_books.sh
```

### Re-indexar Completo

```bash
./reindex_optimized.sh
```

---

## 5. Backups

### Crear Backup

```bash
# Solo base de datos
cp data/rag_system.db data/backups/rag_system_$(date +%Y%m%d_%H%M%S).db

# Base de datos + ChromaDB
cp data/rag_system.db data/backups/rag_system_$(date +%Y%m%d_%H%M%S).db
cp -r data/chroma data/backups/chroma_$(date +%Y%m%d_%H%M%S)

# Backup completo
tar czf backups/v2_full_$(date +%Y%m%d_%H%M%S).tar.gz \
  data/rag_system.db data/chroma/ .env app/ frontend/
```

### Restaurar

```bash
pkill -f "uvicorn app.main:app"
cp data/backups/rag_system_FECHA.db data/rag_system.db
# Reiniciar backend
```

---

## 6. Cloudflare Tunnel

### Verificar

```bash
ps aux | grep cloudflared | grep -v grep
curl -s https://api.bohrbot.space/health
```

### Reiniciar

```bash
pkill -f cloudflared; sleep 2
nohup cloudflared tunnel run bohr-tunnel > logs/cloudflare_tunnel.log 2>&1 &
```

### Mapeo de URLs

| URL publica | Destino local |
|---|---|
| https://api.bohrbot.space | http://localhost:8000 |
| https://chat.bohrbot.space | http://localhost:9000 |

Config: `~/.cloudflared/config.yml`

---

## 7. Checklist Semanal

- [ ] `curl http://localhost:8000/health` responde OK
- [ ] `curl https://api.bohrbot.space/health` responde OK
- [ ] `curl http://localhost:11434/api/tags` muestra nomic-embed-text
- [ ] No hay errores recientes en logs
- [ ] Espacio en disco suficiente: `df -h .`
- [ ] Backup de base de datos creado
- [ ] Revisar reporte de participacion (boton Analytics)

---

## 8. Procedimientos de Inicio/Fin de Semestre

### Inicio de Semestre

1. Obtener lista de alumnos (CSV con Email y Cuenta)
2. Registrar alumnos masivamente (ver seccion 1)
3. Verificar que todos pueden hacer login
4. Compartir URL: https://chat.bohrbot.space
5. Los alumnos veran el modal de bienvenida en su primer acceso automaticamente

### Fin de Semestre

1. Generar reporte de participacion: `python analyze_participation.py`
2. Exportar historial individual de alumnos si se requiere (ver seccion 3)
3. Crear backup completo
4. Opcional: limpiar conversaciones antiguas
5. Opcional: eliminar usuarios del semestre pasado
