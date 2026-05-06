# Gestión de Base de Datos - RAG v2

Este documento describe todas las herramientas disponibles para gestionar la base de datos SQLite del sistema RAG v2.

## 📋 Tabla de Contenidos

1. [Scripts Disponibles](#scripts-disponibles)
2. [Gestor Interactivo](#gestor-interactivo)
3. [Listar Usuarios](#listar-usuarios)
4. [Limpiar Base de Datos](#limpiar-base-de-datos)
5. [Casos de Uso Comunes](#casos-de-uso-comunes)
6. [Backups](#backups)

---

## 🛠️ Scripts Disponibles

| Script | Descripción |
|--------|-------------|
| `db_manager.sh` | **Gestor interactivo** con menú para todas las operaciones |
| `list_users.py` | Lista usuarios con estadísticas |
| `clean_database.py` | Limpia/resetea la base de datos |

---

## 🎛️ Gestor Interactivo

### Uso Básico

```bash
cd /home/medel/BOHR/RAG-API-versions/v2
./db_manager.sh
```

### Menú de Opciones

```
╔════════════════════════════════════════════════════════════╗
║         GESTOR DE BASE DE DATOS - RAG v2                  ║
╚════════════════════════════════════════════════════════════╝

1. Listar usuarios
2. Listar usuarios con estadísticas detalladas
3. Ver estadísticas de la base de datos
4. Limpiar solo conversaciones y mensajes
5. Limpiar solo exámenes
6. Limpiar analytics (query_logs, student_progress)
7. Limpiar usuarios (mantener admin)
8. LIMPIAR TODO (mantener admin)
9. LIMPIAR TODO (incluyendo admin)
10. Exportar usuarios a CSV
0. Salir
```

---

## 👥 Listar Usuarios

### 1. Lista Simple

```bash
python list_users.py
```

**Salida:**
```
============================================================
👥 USUARIOS EN LA BASE DE DATOS
============================================================
+----+----------+-------------------------------------+------------------+-------+------------------+
| ID | Usuario  | Email                               | Nombre Completo  | Admin | Fecha Creación   |
+----+----------+-------------------------------------+------------------+-------+------------------+
| 1  | demo     | demo@example.com                    | Demo User        | ❌     | 2025-10-26 23:51 |
| 4  | G01E001  | ismaelari224@gmail.com              | ARIAS HERNANDEZ  | ❌     | 2025-11-05 04:33 |
+----+----------+-------------------------------------+------------------+-------+------------------+

Total: 2 usuario(s)
```

### 2. Con Estadísticas Detalladas

```bash
python list_users.py --details
```

**Salida adicional:**
```
📊 ESTADÍSTICAS POR USUARIO
============================================================
🔹 Usuario: demo (ID: 1)
------------------------------------------------------------
  Conversaciones: 5
  Mensajes: 42
  Exámenes: 1
  Queries: 28
  Progreso registrado: ✅
```

### 3. Solo Administradores

```bash
python list_users.py --admin-only
```

### 4. Exportar a CSV

```bash
python list_users.py --export
python list_users.py --export --output mis_usuarios.csv
```

**CSV generado:**
```csv
USERNAME,EMAIL,FULL_NAME,IS_ADMIN,CREATED_AT
demo,demo@example.com,Demo User,0,2025-10-26 23:51:00
G01E001,ismaelari224@gmail.com,ARIAS HERNANDEZ ISMAEL,0,2025-11-05 04:33:00
```

---

## 🧹 Limpiar Base de Datos

### 1. Ver Estadísticas (sin modificar)

```bash
python clean_database.py --stats
```

**Salida:**
```
📊 ESTADÍSTICAS DE LA BASE DE DATOS
============================================================
Ruta: /home/medel/BOHR/RAG-API-versions/v2/data/rag_system.db
Tamaño: 404.00 KB

Registros por tabla:
------------------------------------------------------------
  users               :     30 registros
  conversations       :     42 registros
  messages            :    223 registros
  query_logs          :    122 registros
  student_progress    :      3 registros
  exams               :      3 registros
  exam_responses      :     15 registros
  exam_results        :      3 registros
------------------------------------------------------------
  TOTAL               :    441 registros
```

### 2. Limpiar Conversaciones y Mensajes

```bash
python clean_database.py --conversations
```

**Qué elimina:**
- ❌ Todas las conversaciones
- ❌ Todos los mensajes
- ✅ Mantiene: usuarios, exámenes, analytics

### 3. Limpiar Exámenes

```bash
python clean_database.py --exams
```

**Qué elimina:**
- ❌ Todos los exámenes
- ❌ Todas las respuestas de exámenes
- ❌ Todos los resultados de exámenes
- ✅ Mantiene: usuarios, conversaciones, analytics

### 4. Limpiar Analytics

```bash
python clean_database.py --analytics
```

**Qué elimina:**
- ❌ Query logs
- ❌ Student progress
- ✅ Mantiene: usuarios, conversaciones, exámenes

### 5. Limpiar Usuarios (mantener admin)

```bash
python clean_database.py --users --keep-admin
```

**Qué elimina:**
- ❌ Usuarios no-admin
- ❌ Todas sus conversaciones
- ❌ Todos sus exámenes
- ❌ Todo su progreso
- ✅ Mantiene: usuarios admin

### 6. LIMPIAR TODO (mantener admin)

```bash
python clean_database.py --all --keep-admin
```

**Qué elimina:**
- ❌ Todas las conversaciones
- ❌ Todos los mensajes
- ❌ Todos los exámenes
- ❌ Todo el analytics
- ❌ Usuarios no-admin
- ✅ Mantiene: usuarios admin

### 7. LIMPIAR TODO (incluyendo admin) ⚠️ PELIGROSO

```bash
python clean_database.py --all --no-keep-admin
```

**Qué elimina:**
- ❌ **TODO** (reset completo de la base de datos)

### 8. Sin Backup (¡PELIGROSO!)

Por defecto, todos los comandos crean backup automático. Para omitir:

```bash
python clean_database.py --all --no-backup
```

---

## 💼 Casos de Uso Comunes

### Caso 1: Inicio de Semestre (limpiar datos de prueba)

```bash
# 1. Ver qué hay actualmente
python clean_database.py --stats

# 2. Limpiar usuarios de prueba, mantener estructura
python clean_database.py --users --keep-admin

# 3. Cargar nuevos estudiantes
python bulk_create_users_custom.py estudiantes_2025_1.csv

# 4. Verificar
python list_users.py
```

### Caso 2: Limpiar Conversaciones Viejas (mantener usuarios)

```bash
# Mantiene usuarios y exámenes, solo limpia chats
python clean_database.py --conversations
```

### Caso 3: Reset Completo para Nueva Generación

```bash
# 1. Backup manual adicional
cp data/rag_system.db data/backups/rag_system_generacion_2024_2.db

# 2. Limpiar todo (mantener admin)
python clean_database.py --all --keep-admin

# 3. Cargar nuevos estudiantes
python bulk_create_users_custom.py estudiantes_2025_1.csv
```

### Caso 4: Exportar Datos Antes de Limpiar

```bash
# 1. Exportar usuarios
python list_users.py --export --output backup_usuarios_2024.csv

# 2. Ver estadísticas
python clean_database.py --stats

# 3. Limpiar
python clean_database.py --all
```

### Caso 5: Verificar Estudiantes Cargados

```bash
# Lista compacta
python list_users.py

# Con estadísticas de uso
python list_users.py --details
```

---

## 💾 Backups

### Ubicación de Backups

```
/home/medel/BOHR/RAG-API-versions/v2/data/backups/
```

### Backups Automáticos

Todos los comandos de limpieza crean backup automático con timestamp:

```
rag_system_backup_20251105_043310.db
```

### Restaurar desde Backup

```bash
# 1. Detener servidor
pkill -f "uvicorn app.main:app"

# 2. Restaurar backup
cp data/backups/rag_system_backup_20251105_043310.db data/rag_system.db

# 3. Reiniciar servidor
cd /home/medel/BOHR/RAG-API-versions/v2
eval "$(conda shell.bash hook)"
conda activate bohrenv
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### Backup Manual

```bash
# Crear backup manual con nombre descriptivo
cp data/rag_system.db data/backups/rag_system_antes_limpieza_$(date +%Y%m%d).db
```

---

## 🔐 Seguridad

### Confirmación Requerida

Todos los comandos de limpieza requieren confirmación manual:

```bash
⚠️  ADVERTENCIA: Esta acción eliminará datos permanentemente

¿Continuar? (escribe 'SI' para confirmar): SI
```

**IMPORTANTE:** Debes escribir exactamente `SI` (mayúsculas) para confirmar.

### Orden de Eliminación

El script respeta las foreign keys de SQLite eliminando en el orden correcto:

1. `exam_results` (resultados de exámenes)
2. `exam_responses` (respuestas)
3. `exams` (exámenes)
4. `messages` (mensajes)
5. `conversations` (conversaciones)
6. `query_logs` (logs de queries)
7. `student_progress` (progreso)
8. `users` (usuarios - al final)

---

## 📊 Esquema de la Base de Datos

```
users (30 registros)
├── conversations (42 registros)
│   └── messages (223 registros)
├── exams (3 registros)
│   ├── exam_responses (15 registros)
│   └── exam_results (3 registros)
├── query_logs (122 registros)
└── student_progress (3 registros)
```

---

## ⚙️ Opciones Avanzadas

### Combinar Múltiples Operaciones

```bash
# Limpiar conversaciones Y exámenes en un solo comando
python clean_database.py --conversations --exams
```

### Resetear Contadores de Auto-Incremento

```bash
# Resetea IDs a empezar desde 1
python clean_database.py --all --reset-autoincrement
```

### Ver Ayuda Completa

```bash
python clean_database.py --help
python list_users.py --help
```

---

## 🚨 Troubleshooting

### Error: "Base de datos no encontrada"

```bash
# Verificar ruta
ls -lh data/rag_system.db

# Si no existe, el servidor la creará en el próximo arranque
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Error: "Database is locked"

```bash
# Detener servidor primero
pkill -f "uvicorn app.main:app"

# Luego ejecutar limpieza
python clean_database.py --stats
```

### Recuperar de Backup

```bash
# Listar backups disponibles
ls -lht data/backups/

# Restaurar el más reciente
cp data/backups/rag_system_backup_YYYYMMDD_HHMMSS.db data/rag_system.db
```

---

## 📝 Notas Importantes

1. **Siempre** verifica con `--stats` antes de limpiar
2. Los backups se crean automáticamente (puedes omitir con `--no-backup`)
3. La confirmación manual previene eliminaciones accidentales
4. Los usuarios admin se mantienen por defecto (usa `--no-keep-admin` para eliminarlos)
5. El servidor NO necesita reiniciarse después de limpiar la DB

---

## 📞 Contacto y Soporte

Para reportar problemas o sugerencias:
- Abrir issue en el repositorio
- Contactar al administrador del sistema