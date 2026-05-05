#!/bin/bash

# Script para configurar las credenciales del Cloudflare Tunnel

echo "======================================"
echo "Configuración de Cloudflare Tunnel"
echo "======================================"
echo ""

TUNNEL_ID="d72aafcf-191c-4642-be15-83b322945c3d"
TUNNEL_NAME="bohrbot"
CREDENTIALS_FILE="$HOME/.cloudflared/${TUNNEL_ID}.json"

echo "🔍 Verificando estado actual..."
echo ""

# Verificar si cloudflared está instalado
if ! command -v cloudflared &> /dev/null; then
    echo "❌ Error: cloudflared no está instalado"
    echo "Instálalo con: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb && sudo dpkg -i cloudflared.deb"
    exit 1
fi

echo "✅ cloudflared instalado"

# Verificar si el archivo de credenciales existe
if [ -f "$CREDENTIALS_FILE" ]; then
    echo "✅ Archivo de credenciales encontrado en: $CREDENTIALS_FILE"
    echo ""
    echo "El tunnel debería funcionar correctamente."
    echo "Prueba ejecutar: cloudflared tunnel run $TUNNEL_NAME"
    exit 0
fi

echo "⚠️  Archivo de credenciales NO encontrado"
echo ""
echo "📋 Opciones para obtener las credenciales:"
echo ""
echo "OPCIÓN 1: Descargar desde Cloudflare Dashboard"
echo "  1. Ve a https://dash.cloudflare.com"
echo "  2. Zero Trust → Networks → Tunnels"
echo "  3. Busca el tunnel '$TUNNEL_NAME'"
echo "  4. Click en los 3 puntos → 'Configure'"
echo "  5. Baja hasta 'Connector credentials'"
echo "  6. Copia el contenido JSON"
echo "  7. Guárdalo en: $CREDENTIALS_FILE"
echo ""
echo "OPCIÓN 2: Usar cloudflared login (recomendado)"
echo "  Ejecuta: cloudflared tunnel login"
echo "  Luego: cloudflared tunnel token $TUNNEL_ID"
echo "  Copia el token y ejecuta: cloudflared tunnel run --token <TOKEN>"
echo ""
echo "OPCIÓN 3: Recrear el tunnel (último recurso)"
echo "  1. cloudflared tunnel delete $TUNNEL_NAME"
echo "  2. cloudflared tunnel create $TUNNEL_NAME"
echo "  3. Actualiza DNS en Cloudflare con el nuevo tunnel ID"
echo ""

# Mostrar información del tunnel actual
echo "📊 Información del tunnel actual:"
cloudflared tunnel info $TUNNEL_ID

echo ""
echo "======================================"
echo "Siguiente paso:"
echo "======================================"
echo ""
echo "Si tienes acceso al Dashboard de Cloudflare, usa la OPCIÓN 1."
echo "De lo contrario, intenta la OPCIÓN 2 con 'cloudflared tunnel login'."
echo ""