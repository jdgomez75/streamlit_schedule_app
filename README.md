# 🌸 Bella Clinic - Sistema de Reservas

Sistema de reservas para clínicas de belleza con integración a n8n y Mercado Pago.

## 📋 Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta en n8n (para automatizaciones)
- Cuenta en Mercado Pago (para pagos)

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
mkdir bella-clinic
cd bella-clinic
```

### 2. Crear los archivos

Crea los siguientes archivos en tu directorio:
- `app.py` (aplicación principal)
- `database.py` (gestión de base de datos)
- `requirements.txt` (dependencias)
- `.env` (configuración - ver abajo)

### 3. Crear entorno virtual (recomendado)

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate

# En Mac/Linux:
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Configuración de n8n
N8N_WEBHOOK_URL=https://n8n.tu-dominio.com/webhook/booking-confirmed
N8N_CHAT_WEBHOOK_URL=https://n8n.tu-dominio.com/webhook/chat

# Configuración de Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=tu_access_token_aqui
MERCADOPAGO_PUBLIC_KEY=tu_public_key_aqui

# URL de tu aplicación (para callbacks)
APP_URL=https://tu-app.streamlit.app

# Nombre de la clínica
CLINIC_NAME=Bella Clinic
CLINIC_PHONE=5512345678
CLINIC_EMAIL=contacto@bellaclinic.com
```

## ▶️ Ejecutar la Aplicación

### Portal de Clientas (Frontend público)
```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

### Panel de Administración
```bash
streamlit run admin.py --server.port 8502
```

El panel admin se abrirá en `http://localhost:8502`

**💡 Tip:** Puedes correr ambas apps simultáneamente en diferentes puertos para probar la experiencia completa.

## 📱 Estructura del Proyecto

```
bella-clinic/
│
├── app.py                 # Aplicación principal Streamlit
├── database.py            # Gestión de base de datos SQLite
├── requirements.txt       # Dependencias Python
├── .env                   # Variables de entorno (NO subir a Git)
├── bella_clinic.db        # Base de datos SQLite (se crea automáticamente)
└── README.md             # Este archivo
```

## 🔧 Configuración de n8n

### Webhook para Confirmación de Reservas

Crea un workflow en n8n con:

1. **Webhook Node** (trigger)
   - Método: POST
   - Path: `/webhook/booking-confirmed`
   - Responde con: JSON

2. **Function Node** (procesar datos)
   ```javascript
   const booking = $input.item.json;
   
   return {
     phone: booking.client.phone,
     name: booking.client.name,
     date: booking.appointment.day,
     time: booking.appointment.start_time,
     services: booking.services.map(s => s.name).join(', '),
     professional: booking.professional.name,
     total: booking.payment.total,
     deposit: booking.payment.deposit
   };
   ```

3. **WhatsApp Business Node** (enviar confirmación)
   - Número destino: `{{$json.phone}}`
   - Mensaje:
   ```
   ✨ *¡Reserva Confirmada!* ✨
   
   Hola {{$json.name}} 💖
   
   Tu cita está confirmada:
   📅 {{$json.date}} a las {{$json.time}}
   💅 Servicios: {{$json.services}}
   👩‍🦰 Con: {{$json.professional}}
   
   💰 Total: ${{$json.total}}
   ✅ Anticipo pagado: ${{$json.deposit}}
   
   ¡Te esperamos! 🌸
   Bella Clinic
   ```

4. **Wait Node** (24 horas antes)

5. **WhatsApp Business Node** (recordatorio)
   - Mensaje:
   ```
   ⏰ *Recordatorio de Cita*
   
   Hola {{$json.name}},
   
   Te recordamos tu cita mañana:
   📅 {{$json.date}} a las {{$json.time}}
   
   Si necesitas reagendar, contáctanos.
   
   ¡Nos vemos pronto! 💖
   Bella Clinic
   ```

### Webhook para Chat Bot

Crea otro workflow para el chat:

1. **Webhook Node** (trigger)
   - Path: `/webhook/chat`
   - Método: POST

2. **OpenAI Node** o **Claude Node** (responder preguntas)
   - Prompt del sistema:
   ```
   Eres la asistente virtual de Bella Clinic, una clínica de belleza.
   Respondes preguntas sobre servicios, precios, horarios y reservas.
   Eres amigable, profesional y usas emojis ocasionalmente.
   ```

3. **Return Node** (enviar respuesta)

## 💳 Configuración de Mercado Pago

1. Crea una cuenta en [Mercado Pago para Desarrolladores](https://www.mercadopago.com.mx/developers)

2. Obtén tus credenciales:
   - Access Token (para backend)
   - Public Key (para frontend - no usado en esta versión)

3. Configura las URLs de retorno en tu dashboard:
   - Success: `https://tu-app.streamlit.app/?payment=success`
   - Failure: `https://tu-app.streamlit.app/?payment=failure`
   - Pending: `https://tu-app.streamlit.app/?payment=pending`

4. Configura webhook de notificaciones IPN:
   - URL: `https://n8n.tu-dominio.com/webhook/mercadopago-notification`

### Workflow n8n para Notificaciones de Mercado Pago

1. **Webhook Node** (recibir notificación IPN)
   - Path: `/webhook/mercadopago-notification`

2. **HTTP Request Node** (obtener detalles del pago)
   - URL: `https://api.mercadopago.com/v1/payments/{{$json.data.id}}`
   - Headers: `Authorization: Bearer YOUR_ACCESS_TOKEN`

3. **Function Node** (actualizar estado en BD)
   - Llama a un endpoint de tu app para actualizar el estado

4. **WhatsApp Node** (notificar pago confirmado)

## 🗄️ Base de Datos

La base de datos SQLite se crea automáticamente al ejecutar la aplicación por primera vez.

### Tablas principales:

- `categories` - Categorías de servicios
- `services` - Servicios disponibles
- `professionals` - Profesionales de la clínica
- `professional_services` - Relación profesionales-servicios
- `professional_schedules` - Horarios disponibles
- `clients` - Clientes registrados
- `bookings` - Reservas
- `booking_services` - Servicios en cada reserva

### Datos iniciales

La BD incluye datos de ejemplo:
- 4 categorías (Uñas, Facial, Cabello, Spa)
- 8 servicios
- 3 profesionales
- Horarios para los próximos 14 días

## 🚀 Desplegar a Producción

### Opción 1: Streamlit Cloud (GRATIS)

1. Sube tu código a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. Agrega las variables de entorno en "Advanced settings"
5. Deploy!

### Opción 2: Heroku

```bash
# Instalar Heroku CLI
heroku login

# Crear app
heroku create bella-clinic-app

# Configurar variables
heroku config:set N8N_WEBHOOK_URL=tu_url

# Deploy
git push heroku main
```

### Opción 3: VPS (DigitalOcean, AWS, etc.)

```bash
# Instalar dependencias del sistema
sudo apt update
sudo apt install python3-pip nginx

# Clonar proyecto
git clone tu-repo
cd tu-repo

# Instalar dependencias
pip3 install -r requirements.txt

# Ejecutar con systemd
sudo nano /etc/systemd/system/bella-clinic.service
```

## 📱 Convertir a PWA (Progressive Web App)

Para que las clientas puedan "instalar" la app en sus móviles:

1. Crea `manifest.json` en el directorio del proyecto

2. Agrega al inicio de `app.py`:
```python
st.markdown("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#EC4899">
""", unsafe_allow_html=True)
```

3. Las usuarias podrán "Agregar a Pantalla de Inicio" desde su navegador

## 🔒 Seguridad

### Recomendaciones:

1. **NUNCA** subas el archivo `.env` a Git
   ```bash
   # Agregar a .gitignore
   echo ".env" >> .gitignore
   echo "bella_clinic.db" >> .gitignore
   ```

2. Usa variables de entorno para credenciales

3. Implementa rate limiting para prevenir abuso

4. Valida todos los inputs del usuario

5. Usa HTTPS en producción

## 🐛 Troubleshooting

### Error: "No module named 'streamlit'"
```bash
pip install -r requirements.txt
```

### Error: "database is locked"
```bash
# Cerrar todas las instancias de la app y reiniciar
```

### Webhook de n8n no responde
- Verifica que la URL sea accesible públicamente
- Revisa los logs de n8n
- Prueba con Postman o curl primero

### Mercado Pago no redirige correctamente
- Verifica las URLs de retorno en el dashboard
- Asegúrate de usar HTTPS en producción

## 📞 Soporte

Para dudas o problemas:
- Email: soporte@bellaclinic.com
- WhatsApp: +52 55 1234 5678

## 📄 Licencia

MIT License - Úsalo libremente para tu negocio

## 🎯 Roadmap

- [ ] Panel de administración
- [ ] Reportes y analytics
- [ ] Sistema de recordatorios automáticos
- [ ] Integración con Google Calendar
- [ ] App móvil nativa (React Native)
- [ ] Sistema de reseñas y calificaciones
- [ ] Programa de referidos
- [ ] Multi-idioma

---

¡Hecho con 💖 para emprendedoras en el mundo de la belleza!