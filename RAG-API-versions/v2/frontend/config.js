// Configuración de API según entorno
const API_CONFIG = {
    development: 'http://132.248.102.133:8000',
    // La API vive en api.<dominio>. Se deriva del hostname para que el mismo archivo
    // sirva en chat.pauling.cloud y en chat.bohrbot.space durante la transición.
    production: `https://api.${window.location.hostname.replace(/^(chat|www)\./, '')}`
};

// Detectar entorno
const isDevelopment = window.location.hostname === 'localhost' ||
    window.location.hostname === '132.248.102.133' ||
    window.location.port === '9000';

const API_URL = isDevelopment ? API_CONFIG.development : API_CONFIG.production;

console.log('🌐 Entorno:', isDevelopment ? 'Desarrollo' : 'Producción');
console.log('📡 API URL:', API_URL);
