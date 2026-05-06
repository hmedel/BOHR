# Sistema RAG - Gestión de Versiones

## 📦 Versiones Disponibles

### v1 - Sistema Básico (ESTABLE)
- Puerto backend: 8001
- Puerto frontend: 9001
- Sin autenticación
- Sin historial persistente
- **SIEMPRE FUNCIONAL - FALLBACK**

### v2 - Sistema Completo (EN DESARROLLO)
- Puerto backend: 8000
- Puerto frontend: 9000
- Con autenticación multiusuario
- Historial persistente
- Frontend mejorado (colores UNAM)
- Markdown con fórmulas

## 🔧 Comandos

### Cambiar de versión
```bash
./switch_version.sh
```

### Ver estado
```bash
./status.sh
```

### Rollback de emergencia (volver a v1)
```bash
./rollback.sh
```

## 🚀 Iniciar una versión específica

### v1 (estable):
```bash
cd v1
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > server.log 2>&1 &
cd frontend && nohup python -m http.server 9001 > frontend.log 2>&1 &
```

### v2 (nueva):
```bash
cd v2
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
cd frontend && nohup python -m http.server 9000 > frontend.log 2>&1 &
```

## 📊 Logs
```bash
# v1
tail -f v1/server.log
tail -f v1/frontend/frontend.log

# v2
tail -f v2/server.log
tail -f v2/frontend/frontend.log
```

## 🔄 Workflow de Desarrollo

1. Siempre mantener v1 funcional
2. Desarrollar cambios en v2
3. Probar v2 extensivamente
4. Si algo falla, rollback a v1
5. Una vez v2 estable, puede convertirse en v1
