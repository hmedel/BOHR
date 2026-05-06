# 🚀 Despliegue a Producción - chat.bohrbot.space

Guía completa para desplegar RAG v2 en producción usando Cloudflare Tunnel.

---

## 📋 Información del Sistema

**Tunnel Actual:**
- ID: `d72aafcf-191c-4642-be15-83b322945c3d`
- Nombre: `bohrbot`
- Estado: ✅ Activo (4 conexiones)

**Puertos del Sistema:**
- Backend API: `8000`
- Frontend: `9000`

**Dominios Propuestos:**
- Frontend: `https://chat.bohrbot.space`
- Backend API: `https://api.bohrbot.space` (o `https://chat.bohrbot.space/api`)

---

## 🛠️ Scripts Creados

### 1. [`deploy_production.sh`](deploy_production.sh)
Despliegue completo del sistema en producción

### 2. [`update_production.sh`](update_production.sh)
Actualización rápida solo del backend

### 3. [`verify_production.sh`](verify_production.sh)
Verificación completa de servicios

### 4. [`stop_production.sh`](stop_production.sh)
Detener todos los servicios de producción

### 5. [`frontend/config.js`](frontend/config.js)
Configuración auto-detectable de entorno

---

## 🚀 Despliegue Inicial

### Paso 1: Configurar Cloudflare Tunnel

El archivo de configuración se creará automáticamente en: `~/.cloudflared/config.yml`

**Opción A: Frontend y API en subdominios separados**
```yaml
tunnel: d72aafcf-191c-4642-be15-83b322945c3d
credentials-file: /home/medel/.cloudflared/d72aafcf-191c-4642-be15-83b322945c3d.json

ingress:
  - hostname: chat.bohrbot.space
    service: http://localhost:9000
  
  - hostname: api.bohrbot.space
    service: http://localhost:8000
  
  - service: http_status:404
```

**Opción B: Todo bajo chat.bohrbot.space con path /api**
```yaml
tunnel: d72aafcf-191c-4642-be15-83b322945c3d
credentials-file: /home/medel/.cloudflared/d72aafcf-191c-4642-be15-83b322945c3d.json

ingress:
  - hostname: chat.bohrbot.space
    path: ^/api(/.*)?$
    service: http://localhost:8000
  
  - hostname: chat.bohrbot.space
    service: http://localhost:9000
  
  - service: http_status:404
```

### Paso 2: Configurar DNS en Cloudflare

Ve a https://dash.cloudflare.com → Selecciona `bohrbot.space` → DNS

**Para Opción A (subdominios separados):**
```
Tipo: CNAME
Nombre: chat
Destino: d72aafcf-191c-4642-be15-83b322945c3d.cfargotunnel.com
Proxy: ✅ Activado

Tipo: CNAME
Nombre: api
Destino: d72aafcf-191c-4642-be15-83b322945c3d.cfargotunnel.com
Proxy: ✅ Activado
```

**Para Opción B (solo chat):**
```
Tipo: CNAME
Nombre: chat
Destino: d72aafcf-191c-4642-be15-83b322945c3d.cfargotunnel.com
Proxy: ✅ Activado
```

### Paso 3: Desplegar

```bash
cd /home/medel/BOHR/RAG-API-versions/v2

# Despliegue completo (usa token, no requiere archivo de credenciales)
./deploy_production_token.sh
```

El script:
1. ✅ Detiene servicios anteriores
2. ✅ Inicia backend (puerto 8000)
3. ✅ Inicia frontend (puerto 9000)
4. ✅ Verifica servicios locales
5. ✅ Inicia Cloudflare Tunnel con token
6. ✅ Muestra URLs y logs

**Nota:** Este script usa el token del tunnel directamente, por lo que NO necesitas el archivo de credenciales JSON.

---

## 🔍 Verificación

```bash
# Verificar todo
./verify_production.sh

# Ver logs en tiempo real
tail -f logs/backend_production.log
tail -f logs/frontend_production.log
tail -f logs/cloudflare_tunnel.log

# Verificar URLs públicas
curl https://chat.bohrbot.space
curl https://api.bohrbot.space/health
```

---

## 🔄 Actualizar Backend

```bash
# Reinicia solo el backend sin tocar frontend ni tunnel
./update_production.sh
```

---

## 🛑 Detener Producción

```bash
# Detiene todos los servicios
./stop_production.sh
```

---

## 📊 Monitoreo

### Procesos Activos

```bash
ps aux | grep -E "(uvicorn|http.server|cloudflared)" | grep -v grep
```

### Logs

```bash
# Últimas 50 líneas de cada servicio
tail -50 logs/backend_production.log
tail -50 logs/frontend_production.log
tail -50 logs/cloudflare_tunnel.log

# Seguir logs en tiempo real (Ctrl+C para salir)
tail -f logs/backend_production.log
```

### Health Check

```bash
# Local
curl http://localhost:8000/health
curl http://localhost:9000

# Producción
curl https://chat.bohrbot.space
curl https://api.bohrbot.space/health
```

---

## ⚙️ Configuración del Frontend

El frontend usa **auto-detección de entorno**:

- **Desarrollo** (localhost o 132.248.102.133): 
  - API: `http://132.248.102.133:8000`
  
- **Producción** (chat.bohrbot.space):
  - API: `https://api.bohrbot.space` (o `https://chat.bohrbot.space/api`)

No necesitas cambiar nada manualmente. El archivo `frontend/config.js` detecta automáticamente el entorno.

---

## 🔧 Troubleshooting

### Problema: Archivo de credenciales faltante

Si ves el error: `Tunnel credentials file doesn't exist or is not a file`

**Solución:** Usa [`deploy_production_token.sh`](deploy_production_token.sh) en lugar de `deploy_production.sh`

Este script usa el token del tunnel directamente y no requiere el archivo JSON de credenciales.

```bash
./deploy_production_token.sh
```

### Problema: Backend no inicia

```bash
# Ver errores
tail -50 logs/backend_production.log

# Verificar puerto
sudo lsof -i :8000

# Reiniciar manualmente
cd /home/medel/BOHR/RAG-API-versions/v2
eval "$(conda shell.bash hook)"
conda activate bohrenv
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Problema: Tunnel no conecta

```bash
# Ver logs del tunnel
tail -50 logs/cloudflare_tunnel.log

# Verificar configuración
cat ~/.cloudflared/config.yml

# Reiniciar tunnel manualmente
cloudflared tunnel run bohrbot
```

### Problema: DNS no propaga

```bash
# Verificar propagación DNS
nslookup chat.bohrbot.space
nslookup api.bohrbot.space

# Puede tomar 5-10 minutos
# Cloudflare suele ser muy rápido (~2 minutos)
```

### Problema: CORS errors

Si ves errores CORS en el navegador:

1. Verifica que `frontend/config.js` tenga la URL correcta
2. Verifica que el backend acepte requests de tu dominio
3. Revisa `app/main.py` líneas de CORS

---

## 📝 Checklist de Despliegue

```
☐ 1. Cloudflared instalado ✅
☐ 2. Tunnel "bohrbot" existente ✅
☐ 3. ~/.cloudflared/config.yml configurado
☐ 4. DNS CNAME records creados en Cloudflare
☐ 5. Backend funciona localmente (puerto 8000)
☐ 6. Frontend funciona localmente (puerto 9000)
☐ 7. Base de datos accesible
☐ 8. ChromaDB optimizada
☐ 9. Usuario admin creado
☐ 10. Variables de entorno (.env) configuradas

Cuando todo esté ☑, ejecuta:
./deploy_production.sh
```

---

## 🌐 URLs Finales

Una vez desplegado, tu sistema estará disponible en:

- **Frontend**: https://chat.bohrbot.space
- **API**: https://api.bohrbot.space
- **Health Check**: https://api.bohrbot.space/health
- **Docs**: https://api.bohrbot.space/docs

---

## 🔐 Credenciales de Producción

**Admin:**
```
URL: https://chat.bohrbot.space
Username: admin
Password: admin123
```

**Estudiantes:**
```
Username: G01E001, G01E002, ..., G01E027
Passwords: Según CSV
```

---

## 📦 Estructura de Logs

```
logs/
├── backend_production.log      # Logs del servidor FastAPI
├── frontend_production.log     # Logs del servidor HTTP del frontend
└── cloudflare_tunnel.log       # Logs del tunnel de Cloudflare
```

---

## ⚡ Comandos Rápidos

```bash
# Desplegar
./deploy_production.sh

# Verificar
./verify_production.sh

# Ver logs
tail -f logs/backend_production.log

# Actualizar backend
./update_production.sh

# Detener todo
./stop_production.sh

# Reiniciar todo
./stop_production.sh && ./deploy_production.sh
```

---

## 🎯 Próximos Pasos

1. ✅ Ejecutar `./deploy_production_token.sh`
2. ⏳ Esperar propagación DNS (2-5 min, Cloudflare es rápido)
3. ✅ Verificar con `./verify_production.sh`
4. ✅ Probar login en https://chat.bohrbot.space
5. 🎉 ¡Sistema en producción!

## 📌 Scripts Disponibles

- **[`deploy_production_token.sh`](deploy_production_token.sh)** - Despliegue con token (recomendado, no requiere archivo JSON)
- **[`deploy_production.sh`](deploy_production.sh)** - Despliegue con archivo de credenciales (requiere JSON)
- **[`setup_tunnel_credentials.sh`](setup_tunnel_credentials.sh)** - Ayuda para obtener credenciales si las necesitas