"""
Utilidades y funciones auxiliares para Bella Clinic
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Cargar variables de entorno
load_dotenv()

def get_env_var(key, default=None, required=False):
    """Obtiene variable de entorno con validación"""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Variable de entorno requerida no encontrada: {key}")
    return value

# Configuración global
class Config:
    """Clase de configuración centralizada"""
    
    # n8n
    N8N_WEBHOOK_URL = get_env_var('N8N_WEBHOOK_URL', required=True)
    N8N_CHAT_WEBHOOK_URL = get_env_var('N8N_CHAT_WEBHOOK_URL')
    N8N_MERCADOPAGO_WEBHOOK = get_env_var('N8N_MERCADOPAGO_WEBHOOK')
    
    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN = get_env_var('MERCADOPAGO_ACCESS_TOKEN', required=True)
    MERCADOPAGO_PUBLIC_KEY = get_env_var('MERCADOPAGO_PUBLIC_KEY')
    MERCADOPAGO_MODE = get_env_var('MERCADOPAGO_MODE', 'test')
    
    # App
    APP_URL = get_env_var('APP_URL', 'http://localhost:8501')
    
    # Clínica
    CLINIC_NAME = get_env_var('CLINIC_NAME', 'Bella Clinic')
    CLINIC_PHONE = get_env_var('CLINIC_PHONE', '5512345678')
    CLINIC_EMAIL = get_env_var('CLINIC_EMAIL', 'contacto@bellaclinic.com')
    CLINIC_ADDRESS = get_env_var('CLINIC_ADDRESS', '')
    
    # Base de datos
    DATABASE_NAME = get_env_var('DATABASE_NAME', 'bella_clinic.db')
    
    # Configuración de negocio
    DEPOSIT_PERCENTAGE = float(get_env_var('DEPOSIT_PERCENTAGE', '0.5'))
    OPENING_HOUR = int(get_env_var('OPENING_HOUR', '9'))
    CLOSING_HOUR = int(get_env_var('CLOSING_HOUR', '20'))
    MIN_SLOT_DURATION = int(get_env_var('MIN_SLOT_DURATION', '30'))
    BOOKING_DAYS_AHEAD = int(get_env_var('BOOKING_DAYS_AHEAD', '14'))
    REMINDER_HOURS_BEFORE = int(get_env_var('REMINDER_HOURS_BEFORE', '24'))
    
    # Sistema de puntos
    POINTS_PER_PESO = int(get_env_var('POINTS_PER_PESO', '1'))
    POINTS_FOR_FREE_MANICURE = int(get_env_var('POINTS_FOR_FREE_MANICURE', '300'))
    
    # Debug
    DEBUG_MODE = get_env_var('DEBUG_MODE', 'false').lower() == 'true'

def format_currency(amount):
    """Formatea cantidad como moneda mexicana"""
    return f"${amount:,.2f} MXN"

def format_phone(phone):
    """Formatea número telefónico mexicano"""
    # Remover espacios y caracteres especiales
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Agregar código de país si no lo tiene
    if len(clean_phone) == 10:
        clean_phone = '52' + clean_phone
    
    return clean_phone

def validate_email(email):
    """Valida formato de email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def calculate_end_time(start_time, duration_minutes):
    """Calcula hora de fin dado inicio y duración"""
    start_hour, start_min = map(int, start_time.split(':'))
    start_total_minutes = start_hour * 60 + start_min
    end_total_minutes = start_total_minutes + duration_minutes
    
    end_hour = end_total_minutes // 60
    end_min = end_total_minutes % 60
    
    return f"{end_hour:02d}:{end_min:02d}"

def generate_booking_reference():
    """Genera referencia única para reserva"""
    import random
    import string
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"BC-{timestamp}-{random_str}"

def get_weekday_name(date_str):
    """Obtiene nombre del día de la semana en español"""
    weekdays = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return weekdays[date_obj.weekday()]

def is_business_hours(time_str):
    """Verifica si una hora está dentro del horario de trabajo"""
    hour = int(time_str.split(':')[0])
    return Config.OPENING_HOUR <= hour < Config.CLOSING_HOUR

def calculate_points_earned(amount):
    """Calcula puntos ganados por una compra"""
    return int(amount * Config.POINTS_PER_PESO)

def format_services_list(services):
    """Formatea lista de servicios para mensajes"""
    if not services:
        return "Ningún servicio"
    
    if len(services) == 1:
        return services[0]['name']
    
    return ', '.join([s['name'] for s in services[:-1]]) + f" y {services[-1]['name']}"

def get_whatsapp_message_template(message_type, data):
    """Genera plantillas de mensajes de WhatsApp"""
    
    templates = {
        'confirmation': f"""
✨ *¡Reserva Confirmada!* ✨

Hola {data['client_name']} 💖

Tu cita está confirmada:
📅 {data['date']} a las {data['time']}
💅 Servicios: {data['services']}
👩‍🦰 Con: {data['professional']}

💰 Total: {format_currency(data['total'])}
✅ Anticipo pagado: {format_currency(data['deposit'])}
💵 A pagar en clínica: {format_currency(data['remaining'])}

¡Te esperamos! 🌸
{Config.CLINIC_NAME}
📍 {Config.CLINIC_ADDRESS}
📞 {Config.CLINIC_PHONE}
""",
        
        'reminder': f"""
⏰ *Recordatorio de Cita*

Hola {data['client_name']},

Te recordamos tu cita mañana:
📅 {data['date']} a las {data['time']}
💅 Servicios: {data['services']}

Si necesitas reagendar, contáctanos lo antes posible.

¡Nos vemos pronto! 💖
{Config.CLINIC_NAME}
📞 {Config.CLINIC_PHONE}
""",
        
        'payment_confirmed': f"""
✅ *Pago Confirmado*

Hola {data['client_name']},

Tu pago de {format_currency(data['amount'])} ha sido confirmado.

📋 Referencia: {data['reference']}

¡Gracias por tu pago! Nos vemos en tu cita. 💖
{Config.CLINIC_NAME}
""",
        
        'cancellation': f"""
❌ *Cita Cancelada*

Hola {data['client_name']},

Tu cita del {data['date']} a las {data['time']} ha sido cancelada.

El reembolso de tu anticipo se procesará en 5-7 días hábiles.

Si fue un error, contáctanos para reagendar.

{Config.CLINIC_NAME}
📞 {Config.CLINIC_PHONE}
"""
    }
    
    return templates.get(message_type, "Mensaje no disponible")

def validate_booking_data(data):
    """Valida datos de reserva antes de procesar"""
    errors = []
    
    # Validar nombre
    if not data.get('client_name') or len(data['client_name']) < 2:
        errors.append("Nombre inválido")
    
    # Validar teléfono
    if not data.get('client_phone') or len(data['client_phone']) < 10:
        errors.append("Teléfono inválido")
    
    # Validar email
    if data.get('client_email') and not validate_email(data['client_email']):
        errors.append("Email inválido")
    
    # Validar fecha
    if data.get('date'):
        try:
            booking_date = datetime.strptime(data['date'], '%Y-%m-%d')
            if booking_date < datetime.now():
                errors.append("La fecha no puede ser en el pasado")
        except ValueError:
            errors.append("Formato de fecha inválido")
    
    # Validar servicios
    if not data.get('services') or len(data['services']) == 0:
        errors.append("Debe seleccionar al menos un servicio")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def calculate_discount(services):
    """Calcula descuentos por combos de servicios"""
    total = sum(s['price'] for s in services)
    
    # Descuentos por cantidad
    if len(services) >= 3:
        discount = total * 0.15  # 15% descuento por 3+ servicios
    elif len(services) == 2:
        discount = total * 0.10  # 10% descuento por 2 servicios
    else:
        discount = 0
    
    return {
        'original_price': total,
        'discount_amount': discount,
        'final_price': total - discount,
        'discount_percentage': (discount / total * 100) if total > 0 else 0
    }

def get_popular_service_combos():
    """Obtiene combos populares de servicios"""
    # Esto podría calcularse de la BD en producción
    return [
        {
            'name': 'Paquete Manos Perfectas',
            'services': ['Manicure Francesa', 'Pedicure Spa'],
            'discount': 7
        },
        {
            'name': 'Paquete Renovación',
            'services': ['Facial Hidratante', 'Manicure Francesa'],
            'discount': 10
        },
        {
            'name': 'Paquete Glam Completo',
            'services': ['Tinte + Corte', 'Facial Hidratante'],
            'discount': 20
        }
    ]

def log_activity(activity_type, details):
    """Registra actividad del sistema"""
    if Config.DEBUG_MODE:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {activity_type}: {details}")

def sanitize_input(text):
    """Limpia input del usuario"""
    if not text:
        return ""
    
    # Remover caracteres especiales peligrosos
    import html
    return html.escape(text.strip())

# Decorador para medir tiempo de ejecución
def timer_decorator(func):
    """Decorador para medir tiempo de ejecución de funciones"""
    import time
    
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        
        if Config.DEBUG_MODE:
            print(f"⏱️ {func.__name__} tardó {end - start:.2f} segundos")
        
        return result
    
    return wrapper

# Función para testing
def run_tests():
    """Ejecuta tests básicos de las utilidades"""
    print("🧪 Ejecutando tests...\n")
    
    # Test 1: Formateo de moneda
    assert format_currency(100) == "$100.00 MXN"
    print("✅ Test 1: Formateo de moneda - PASÓ")
    
    # Test 2: Validación de email
    assert validate_email("test@example.com") == True
    assert validate_email("invalid-email") == False
    print("✅ Test 2: Validación de email - PASÓ")
    
    # Test 3: Cálculo de hora de fin
    assert calculate_end_time("10:00", 90) == "11:30"
    print("✅ Test 3: Cálculo de hora de fin - PASÓ")
    
    # Test 4: Formateo de teléfono
    assert format_phone("5512345678") == "525512345678"
    print("✅ Test 4: Formateo de teléfono - PASÓ")
    
    # Test 5: Cálculo de puntos
    assert calculate_points_earned(100) == 100
    print("✅ Test 5: Cálculo de puntos - PASÓ")
    
    print("\n✅ Todos los tests pasaron correctamente!")

if __name__ == "__main__":
    # Ejecutar tests cuando se corre el archivo directamente
    run_tests()