import streamlit as st
import requests
import json
import os
import src.notifications
from datetime import datetime, timedelta
from src.database import Database

# Configuración de la página
st.set_page_config(
    page_title="Rubí Mata Salón - Reservas",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para diseño "cute"
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #FDF2F8 0%, #FAF5FF 50%, #FDF2F8 100%);
    }
    
    .clinic-header {
        background: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    .service-card {
        background: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
        border: 2px solid transparent;
    }
    
    .service-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(236,72,153,0.3);
        border-color: #EC4899;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 8px 16px rgba(236,72,153,0.4);
    }
    
    .booking-code {
        background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        margin: 1rem 0;
        word-break: break-all;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

CSS_MEJORADO = """
<style>
    /* Carrito flotante */
    .cart-badge {
        background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
        color: white;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.1rem;
        box-shadow: 0 4px 12px rgba(236,72,153,0.4);
        margin: 0 auto;
    }
    
    /* Servicio seleccionado */
    .service-selected {
        border: 2px solid #EC4899 !important;
        background: linear-gradient(135deg, rgba(236,72,153,0.1) 0%, rgba(168,85,247,0.1) 100%) !important;
    }
    
    .service-card.selected {
        border: 2px solid #EC4899;
        box-shadow: 0 8px 12px rgba(236,72,153,0.3);
    }
    
    /* Chip de servicio en carrito */
    .service-chip {
        background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.25rem;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    /* Resumen del carrito */
    .cart-summary {
        background: linear-gradient(135deg, #F0F9FF 0%, #E0E7FF 100%);
        border: 2px solid #EC4899;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    
    /* Total */
    .cart-total {
        background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        margin-top: 1rem;
        font-weight: bold;
        font-size: 1.1rem;
    }
</style>
"""

# Inicializar base de datos
def init_db():
    return Database()

db = init_db()

# Inicializar session state
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'home'
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None
if 'selected_slot' not in st.session_state:
    st.session_state.selected_slot = None
if 'client_info' not in st.session_state:
    st.session_state.client_info = {}
if 'user_points' not in st.session_state:
    st.session_state.user_points = 250
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'current_booking_code' not in st.session_state:
    st.session_state.current_booking_code = None
if 'last_booking_id' not in st.session_state:
    st.session_state.last_booking_id = None
if 'payment_validation_result' not in st.session_state:
    st.session_state.payment_validation_result = None
if 'payment_confirmed' not in st.session_state:
    st.session_state.payment_confirmed = False
if 'payment_error' not in st.session_state:
    st.session_state.payment_error = None

# ==================== FUNCIONES AUXILIARES ====================

def add_to_cart(service):
    st.session_state.cart.append(service)
    st.success(f"✅ {service['name']} agregado a tu cita")

def remove_from_cart(service_id):
    st.session_state.cart = [s for s in st.session_state.cart if s['id'] != service_id]
    st.rerun()

def get_total_price():
    return sum(s['price'] for s in st.session_state.cart)

def get_total_duration():
    return sum(s['duration'] for s in st.session_state.cart)

def calculate_deposit():
    """Calcula el anticipo requerido"""
    if not st.session_state.cart:
        return 0
    
    deposits = [s.get('deposit', s.get('anticipo', 200)) for s in st.session_state.cart]
    return max(deposits)

def calculate_available_slots(date, services):
    """Calcula slots disponibles basado en profesionales y servicios"""
    if not services:
        return []
    
    service_ids = [s['id'] for s in services]
    
    all_professionals = []
    for service in services:
        profs = db.get_professionals_for_service(service['id'])
        for prof_id in profs:
            prof_info = db.get_professional_by_id(prof_id)
            if prof_info and prof_info not in all_professionals:
                all_professionals.append(prof_info)
    
    if not all_professionals:
        return []
    
    slots = []
    total_duration = get_total_duration()
    
    for prof in all_professionals:
        schedule = db.get_professional_schedule(prof['id'], date)
        
        if not schedule:
            continue
        
        # Obtener citas confirmadas del profesional para esa fecha
        booked_slots = db.get_professional_bookings_by_date(prof['id'], date)
        
        for start_time in schedule:
            start_hour, start_min = map(int, start_time.split(':'))
            start_minutes = start_hour * 60 + start_min
            end_minutes = start_minutes + total_duration
            
            if end_minutes <= 19 * 60:
                end_hour = end_minutes // 60
                end_min = end_minutes % 60
                end_time = f"{end_hour:02d}:{end_min:02d}"
                
                # Validar que el horario no esté ocupado
                is_available = True
                for booked in booked_slots:
                    booked_start = booked['start_time']
                    booked_end = booked['end_time']
                    
                    # Convertir a minutos para comparación
                    booked_start_h, booked_start_m = map(int, booked_start.split(':'))
                    booked_start_minutes = booked_start_h * 60 + booked_start_m
                    
                    booked_end_h, booked_end_m = map(int, booked_end.split(':'))
                    booked_end_minutes = booked_end_h * 60 + booked_end_m
                    
                    # Verificar solapamiento
                    if (start_minutes < booked_end_minutes) and (end_minutes > booked_start_minutes):
                        is_available = False
                        break
                
                if is_available:
                    slots.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'professionals': [{
                            'id': prof['id'],
                            'name': prof['name'],
                            'services': [s['name'] for s in services]
                        }],
                        'duration': total_duration,
                        'type': 'single',
                        'description': f"Servicios con {prof['name']}"
                    })
    
    seen = set()
    unique_slots = []
    for slot in sorted(slots, key=lambda x: x['start_time']):
        key = f"{slot['start_time']}_{slot['professionals'][0]['id']}"
        if key not in seen:
            seen.add(key)
            unique_slots.append(slot)
    
    return unique_slots


def send_webhook_to_n8n(booking_data):
    """Envía webhook a n8n con los datos de la reserva"""
    webhook_url = os.getenv('N8N_WEBHOOK_URL')
    
    try:
        response = requests.post(webhook_url, json=booking_data, timeout=10)
        if response.status_code == 200:
            st.success("✅ Confirmación enviada")
        return response.status_code == 200
    except Exception as e:
        st.warning(f"⚠️ No se pudo enviar notificación: {str(e)}")
        return False

def create_mercadopago_preference(booking_data):
    """
    Crea preferencia de pago en Mercado Pago
    
    CONFIGURACIÓN REQUERIDA:
    1. Obtén tu Access Token en: https://www.mercadopago.com/developers/panel
    2. Reemplaza 'TU_ACCESS_TOKEN_AQUI' con tu token real
    3. La URL de retorno se configurará automáticamente
    """
    
    try:
        from mercadopago.sdk import SDK
    except ImportError:
        st.error("❌ Mercado Pago SDK no está instalado. Ejecuta: pip install mercado-pago")
        return None
    
    # ⚠️ IMPORTANTE: Reemplaza esto con tu Access Token real
    # Obtén tu token en: https://www.mercadopago.com/developers/panel/credentials
    ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    
    # Validar que el token sea válido
    if ACCESS_TOKEN == "ACCESS_TOKEN":
        st.warning("""
        ⚠️ **MERCADO PAGO NO CONFIGURADO**
        
        Para activar los pagos:
        1. Ve a: https://www.mercadopago.com/developers/panel/credentials
        2. Copia tu Access Token
        3. En app.py, línea ~199, reemplaza: `ACCESS_TOKEN = "TU_ACCESS_TOKEN_AQUI"`
        4. Pegua tu token real
        5. Guarda y reinicia la app
        """)
        # Retornar URL de prueba para demostración
        booking_code = booking_data.get('booking_code', 'unknown')
        return f"https://www.mercadopago.com.mx/checkout/v1/redirect?preference-id=demo&reference={booking_code}"
    
    try:
        # Inicializar cliente de Mercado Pago
        sdk = SDK(ACCESS_TOKEN)
        
        booking_code = booking_data.get('booking_code', 'unknown')
        deposit = booking_data.get('payment', {}).get('deposit', 0)
        
        # Crear datos de la preferencia
        preference_data = {
            "items": [{
                "title": f"Anticipo - {booking_data['client']['name']}",
                "description": f"Servicios: {', '.join([s['name'] for s in booking_data['services']])}",
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(deposit)
            }],
            "payer": {
                "name": booking_data['client']['name'],
                "email": booking_data['client']['email'],
                "phone": {
                    "area_code": "52",
                    "number": booking_data['client']['phone']
                }
            },
            "external_reference": booking_code,
            "back_urls": {
                "success": "https://tu-dominio.com/success",
                "failure": "https://tu-dominio.com/failure",
                "pending": "https://tu-dominio.com/pending"
            },
            "auto_return": "approved",
            "notification_url": "https://tu-dominio.com/webhook/mercadopago"
        }
        
        # Crear la preferencia
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        if preference and "id" in preference:
            # Retornar el init_point (enlace de pago)
            init_point = preference.get("init_point")
            st.session_state.last_payment_preference_id = preference.get("id")
            return init_point
        else:
            st.error("❌ Error al crear preferencia de Mercado Pago")
            return None
            
    except Exception as e:
        st.error(f"❌ Error de Mercado Pago: {str(e)}")
        return None
    
    # ============================================================================
# PASO 2: FUNCIÓN AUXILIAR - Mostrar carrito resumido
# ============================================================================

def render_cart_summary():
    """
    Muestra un resumen del carrito actual.
    Úsalo en la sección de servicios para mostrar qué está en el carrito.
    """
    if not st.session_state.cart:
        st.info("🛒 Tu carrito está vacío")
        return False
    
    st.markdown("""
    <div class='cart-summary'>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 🛒 Carrito Actual ({len(st.session_state.cart)} servicio{'s' if len(st.session_state.cart) > 1 else ''})")
    
    # Mostrar servicios como chips
    col1, col2 = st.columns([3, 1])
    
    with col1:
        services_html = ""
        for service in st.session_state.cart:
            services_html += f"<span class='service-chip'>{service['name']} - ${service['price']}</span>"
        
        st.markdown(services_html, unsafe_allow_html=True)
    
    with col2:
        # Botón para ver carrito
        if st.button("📋 Ver Carrito", use_container_width=True, key="view_cart_from_services"):
            st.session_state.current_view = 'cart'
            st.rerun()
    
    # Mostrar totales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total", f"${get_total_price()}")
    with col2:
        st.metric("⏱️ Duración", f"{get_total_duration()} min")
    with col3:
        st.metric("🎁 Anticipo", f"${calculate_deposit()}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    return True

# ============================================================================
# PASO 3: FUNCIÓN AUXILIAR - Verificar si servicio está en carrito
# ============================================================================

def is_service_in_cart(service_id):
    """Verifica si un servicio está en el carrito"""
    return any(s['id'] == service_id for s in st.session_state.cart)


# ==================== VISTAS ====================

def render_home():
    """Página de inicio"""
    st.markdown("""
    <div class='clinic-header'>
        <h1>✨ Rubí Mata Salón</h1>
        <p style='font-size: 1.1rem; color: #666;'>
            Tu clínica de belleza integral. Reserva tu cita ahora.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📅 Nueva Reserva", use_container_width=True, key="new_booking"):
            st.session_state.current_view = 'services'
            st.rerun()
    
    with col2:
        if st.button("🔍 Ver mi Cita", use_container_width=True, key="view_booking"):
            st.session_state.current_view = 'manage_booking'
            st.rerun()
    
    with col3:
        if st.button("💬 Contactar", use_container_width=True, key="contact"):
            st.info("📱 WhatsApp: +52 55 6190 7377\n📧 Email: info@rubimatasalon.com.mx")

# ============================================
# REEMPLAZAR en app.py: función render_services()
# ============================================

def render_services():
    """Vista de servicios con categorías desde tabla de BD - VERSIÓN MEJORADA"""
    if st.button("← Volver", key="back_to_home"):
        st.session_state.current_view = 'home'
        st.rerun()
    
    st.markdown("## 💅 Servicios Disponibles")
    st.markdown("---")
    
    # Inicializar session state para categoría seleccionada
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = None
    
    # Obtener categorías desde tabla
    categories = db.get_active_categories()
    
    if not categories:
        st.warning("⚠️ No hay categorías disponibles")
        return
    
    # Mostrar carrito resumido si hay items
    if st.session_state.cart:
        st.markdown("---")
        render_cart_summary()
        st.markdown("---")
    
    # Mostrar botones de categorías
    st.markdown("### 📁 Selecciona una Categoría")
    
    # Crear columnas dinámicamente según número de categorías
    num_cols = min(len(categories), 6)
    cols = st.columns(num_cols)
    
    for idx, category in enumerate(categories):
        with cols[idx % num_cols]:
            category_name = category['name']
            icon = category.get('icon', '📁')
            service_count = category['service_count']
            
            button_label = f"{icon} {category_name}\n({service_count} servicios)"
            
            if st.button(
                button_label,
                key=f"category_{category['id']}",
                use_container_width=True
            ):
                st.session_state.selected_category = category['id']
                st.rerun()
    
    # Mostrar servicios de la categoría seleccionada
    if st.session_state.selected_category:
        selected_cat_id = st.session_state.selected_category
        
        # Obtener la categoría para mostrar su nombre
        selected_category = None
        for cat in categories:
            if cat['id'] == selected_cat_id:
                selected_category = cat
                break
        
        if selected_category:
            # Obtener servicios de la categoría
            category_services = db.get_services_by_category(selected_cat_id)
            
            st.markdown(f"### {selected_category['icon']} Servicios en {selected_category['name']}")
            st.markdown("---")
            
            if not category_services:
                st.info("📭 No hay servicios en esta categoría")
            else:
                # ✅ CAMBIO: Mostrar servicios en columnas de 2
                cols = st.columns(2)
                
                for idx, service in enumerate(category_services):
                    in_cart = is_service_in_cart(service['id'])
                    
                    with cols[idx % 2]:
                        # ✅ CAMBIO: Agregar borde destacado si está en carrito
                        if in_cart:
                            st.markdown(f"""
                            <div class='service-card service-selected'>
                                <h4>✅ {service['name']}</h4>
                                <p style='font-size: 0.9rem; color: #666;'>{service.get('description', '')}</p>
                                <p style='margin-top: 1rem;'>
                                    <strong style='color: #EC4899;'>${service['price']}</strong> | 
                                    <span style='color: #A855F7;'>⏱️ {service['duration']} min</span>
                                </p>
                                <p style='color: #10B981; font-weight: bold; margin-top: 0.5rem;'>✓ En tu carrito</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class='service-card'>
                                <h4>{service['name']}</h4>
                                <p style='font-size: 0.9rem; color: #666;'>{service.get('description', '')}</p>
                                <p style='margin-top: 1rem;'>
                                    <strong style='color: #EC4899;'>${service['price']}</strong> | 
                                    <span style='color: #A855F7;'>⏱️ {service['duration']} min</span>
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # ✅ CAMBIO: Texto diferente si ya está en carrito
                        if in_cart:
                            if st.button(
                                "❌ Remover del carrito",
                                key=f"remove_{service['id']}",
                                use_container_width=True
                            ):
                                remove_from_cart(service['id'])
                                st.rerun()
                        else:
                            if st.button(
                                f"✅ Agregar a tu cita",
                                key=f"add_{service['id']}",
                                use_container_width=True
                            ):
                                add_to_cart(service)
                                st.rerun()
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("← Volver a Categorías", key="back_categories", use_container_width=True):
                    st.session_state.selected_category = None
                    st.rerun()
            
            with col2:
                if st.button("🛒 Ver Carrito", key="view_cart", use_container_width=True):
                    st.session_state.current_view = 'cart'
                    st.rerun()
    else:
        st.info("👆 Selecciona una categoría para ver los servicios disponibles")


# ============================================
# NUEVA FUNCIÓN AUXILIAR
# ============================================

def get_services():
    """
    Obtiene todos los servicios activos
    (Mantener compatible con código existente)
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, name, description, price, duration, 
                category, category_id, deposit, anticipo, active
            FROM services
            WHERE active = TRUE
            ORDER BY name
        """)
        
        services = []
        for row in cursor.fetchall():
            services.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': float(row[3]) if row[3] else 0,
                'duration': row[4],
                'category': row[5],
                'category_id': row[6],
                'deposit': float(row[7]) if row[7] else 0,
                'anticipo': float(row[8]) if row[8] else 0,
                'active': row[9]
            })
        
        return services

def render_cart():
    """Vista del carrito - VERSIÓN MEJORADA"""
    if st.button("← Volver", key="back_to_services"):
        st.session_state.current_view = 'services'
        st.rerun()
    
    st.markdown("## 🛒 Tu Carrito")
    st.markdown("---")
    
    if not st.session_state.cart:
        st.info("Tu carrito está vacío")
        if st.button("🛍️ Seguir comprando", use_container_width=True):
            st.session_state.current_view = 'services'
            st.rerun()
        return
    
    # ✅ CAMBIO: Mostrar servicios con mejor visual
    st.markdown(f"### Servicios en tu carrito ({len(st.session_state.cart)})")
    
    for idx, service in enumerate(st.session_state.cart, 1):
        col1, col2, col3 = st.columns([2, 1.5, 0.5])
        
        with col1:
            st.markdown(f"""
            **{idx}. {service['name']}**
            
            {service.get('description', '')}
            """)
        
        with col2:
            st.markdown(f"""
            💰 ${service['price']}  
            ⏱️ {service['duration']} min
            """)
        
        with col3:
            if st.button("🗑️", key=f"remove_{service['id']}", help="Eliminar del carrito"):
                remove_from_cart(service['id'])
                st.rerun()
    
    st.markdown("---")
    
    # ✅ CAMBIO: Mostrar totales con mejor estilo
    st.markdown(f"""
    <div class='cart-summary'>
    <h3>📊 Resumen de tu Cita</h3>
    
    | Concepto | Valor |
    |----------|-------|
    | 💰 Total de Servicios | ${get_total_price()} MXN |
    | ⏱️ Duración Total | {get_total_duration()} minutos |
    | 🎁 Anticipo a Pagar | ${calculate_deposit()} MXN |
    
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🛍️ Seguir comprando", use_container_width=True, key="continue_shopping"):
            st.session_state.current_view = 'services'
            st.rerun()
    
    with col2:
        if st.button("📅 Seleccionar Fecha y Hora", use_container_width=True, key="proceed_calendar", type="primary"):
            st.session_state.current_view = 'calendar'
            st.rerun()


def render_calendar():
    """Vista de selección de fecha y hora"""
    # Agregar CSS para mejorar responsive
    st.markdown("""
    <style>
    @media (max-width: 640px) {
        [data-testid="column"] {
            flex-basis: 100% !important;
            width: 100% !important;
        }
    }
    @media (min-width: 641px) and (max-width: 1024px) {
        [data-testid="column"] {
            flex-basis: calc(50% - 0.5rem) !important;
            width: calc(50% - 0.5rem) !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("← Volver", key="back_to_cart"):
        st.session_state.current_view = 'cart'
        st.rerun()
    
    st.markdown("## 📅 Selecciona tu Fecha y Hora")
    st.markdown("---")
    
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(0, 30)]
    
    st.markdown("### 📅 Fechas disponibles - Elige tu día preferido")
    
    # Crear grid de 3x3 manualmente
    date_grid = [dates[i:i+3] for i in range(0, min(12, len(dates)), 3)]
    
    for row in date_grid:
        cols = st.columns(3)
        for col_idx, date in enumerate(row):
            weekday = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][date.weekday()]
            date_info = {
                'date': str(date),
                'day': date.strftime('%d/%m'),
                'weekday': weekday
            }
            
            with cols[col_idx]:
                if st.button(f"**{date_info['day']}**\n\n{date_info['weekday']}", 
                            key=f"date_{date_info['date']}", use_container_width=True):
                    st.session_state.selected_date = date_info
                    st.rerun()
    
    if st.session_state.selected_date:
        st.markdown(f"### Horarios disponibles para {st.session_state.selected_date['day']}")
        
        slots = calculate_available_slots(
            st.session_state.selected_date['date'],
            st.session_state.cart
        )
        
        if not slots:
            st.warning("⚠️ No hay horarios disponibles para esta fecha con estos servicios.")
        else:
            st.markdown("### 🕐 Horarios disponibles")
            
            # Preparar opciones de slots
            slot_options = [
                f"{slot['start_time']} - {slot['end_time']} | {slot['professionals'][0]['name']}" 
                for slot in slots
            ]
            
            # Selectbox para elegir horario
            selected_slot_str = st.selectbox(
                "Selecciona tu horario preferido:",
                options=slot_options,
                key="time_slot_select"
            )
            
            if selected_slot_str:
                # Encontrar el slot seleccionado
                selected_slot_idx = slot_options.index(selected_slot_str)
                selected_slot_data = slots[selected_slot_idx]
                
                # Mostrar resumen
                st.info(f"✓ Horario seleccionado: {selected_slot_str}")
                
                if st.button("✅ Confirmar Horario", use_container_width=True, key="confirm_slot"):
                    st.session_state.selected_slot = {
                        'start_time': selected_slot_data['start_time'],
                        'end_time': selected_slot_data['end_time'],
                        'duration': selected_slot_data['duration'],
                        'type': selected_slot_data['type'],
                        'professionals': selected_slot_data['professionals'],
                        'description': selected_slot_data.get('description', '')
                    }
                    st.session_state.current_view = 'checkout'
                    st.rerun()
                            
def render_checkout():
    """Vista de checkout y pago"""
    if st.button("← Volver", key="back_to_calendar"):
        st.session_state.current_view = 'calendar'
        st.rerun()
    
    st.markdown("## 💳 Confirmación y Pago")
    st.markdown("---")
    
    professionals = st.session_state.selected_slot.get('professionals', [])
    
    if professionals:
        prof = professionals[0]
        st.success(f"""
        ### Resumen de tu cita
        
        **Servicios:** {', '.join([s['name'] for s in st.session_state.cart])}  
        **Fecha:** {st.session_state.selected_date['day']}  
        **Hora:** {st.session_state.selected_slot['start_time']} - {st.session_state.selected_slot['end_time']}  
        **Profesional:** {prof['name']}  
        **Duración:** {st.session_state.selected_slot['duration']} minutos
        """)
    
    total = get_total_price()
    deposit = calculate_deposit()
    
    if len(st.session_state.cart) > 1:
        st.markdown("#### 💰 Desglose de Anticipos")
        for service in st.session_state.cart:
            service_deposit = service.get('deposit', service.get('anticipo', 200))
            st.caption(f"• {service['name']}: ${service_deposit}")
        st.markdown(f"**Anticipo requerido:** ${deposit} (el más alto)")
        st.markdown("---")
    
    st.markdown(f"""
    <div style='background: #FCE7F3; padding: 1.5rem; border-radius: 15px; margin: 1rem 0;'>
        <h3 style='color: #EC4899;'>Anticipo a pagar: ${deposit:.0f} MXN</h3>
        <p style='margin: 0.5rem 0;'>Total de servicios: ${total} MXN</p>
        <p style='margin: 0; color: #666;'>Resto en clínica: ${total - deposit:.0f} MXN</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Tus datos")
    
    button_key = f"proceed_payment_{st.session_state.selected_slot['start_time'].replace(':', '')}"
    
    name = st.text_input("Nombre completo *", placeholder="Nombre", key=f"client_name_{button_key}")
    phone = st.text_input("Teléfono (WhatsApp) *", placeholder="5512345678", key=f"client_phone_{button_key}")
    email = st.text_input("Email *", placeholder="maria@ejemplo.com", key=f"client_email_{button_key}")
    
    if st.button("💳 Proceder al Pago", use_container_width=True, type="primary", key=button_key):
        if not all([name, phone, email]):
            st.error("⚠️ Por favor completa todos los campos")
            st.stop()
        
        st.session_state.client_info = {
            'name': name,
            'phone': phone,
            'email': email
        }
        
        prof = professionals[0] if professionals else None
        
        if not prof:
            st.error("❌ Error: No se pudo asignar un profesional")
            st.stop()
        
        # Crear cita con código único
        success, booking_code, booking_id = db.create_booking(
            client_name=name,
            client_phone=phone,
            client_email=email,
            date=st.session_state.selected_date['date'],
            start_time=st.session_state.selected_slot['start_time'],
            end_time=st.session_state.selected_slot['end_time'],
            professional_id=prof.get('id'),
            services=st.session_state.cart,
            total_price=total,
            deposit_paid=0
        )

        # Guardar código de cita en session
        st.session_state.current_booking_code = booking_code
        st.session_state.last_booking_id = booking_id
        
        if not booking_code or not booking_id:
            st.error("❌ Error: No se pudo crear la cita. Intenta de nuevo.")
            st.stop()

        # Crear registro de pago
        success_payment, payment_result = db.create_payment(
            booking_code=booking_code,
            booking_id=booking_id,
            amount=deposit,
            payment_method='deposit',
            payment_status='pending'
        )

        if not success_payment:
            st.error(f"❌ {payment_result}")
            # Opcionalmente, podría cancelarse la cita aquí si no se puede crear el pago
            st.stop()
        
        # Marcar el horario como ocupado en la tabla de schedules
        if booking_code and prof:
            success_schedule, msg_schedule = db.mark_schedule_unavailable_by_date_time(
                professional_id=prof.get('id'),
                date=st.session_state.selected_date['date'],
                start_time=st.session_state.selected_slot['start_time']
            )
            if not success_schedule:
                st.warning(f"⚠️ Aviso: {msg_schedule}")
        
        booking_data = {
            'booking_id': booking_id,
            'booking_code': booking_code,
            'event': 'booking_created',
            'client': st.session_state.client_info,
            'appointment': {
                'date': st.session_state.selected_date['date'],
                'day': st.session_state.selected_date['day'],
                'start_time': st.session_state.selected_slot['start_time'],
                'end_time': st.session_state.selected_slot['end_time'],
                'duration': st.session_state.selected_slot['duration']
            },
            'services': [{'name': s['name'], 'price': float(s['price'])} for s in st.session_state.cart],
            'professional': {
                'id': prof['id'],
                'name': prof['name']
            },
            'payment': {
                'total': float(total),
                'deposit': float(deposit),
                'remaining': float(total - deposit)
            }
        }
        
        payment_url = create_mercadopago_preference(booking_data)
        #send_webhook_to_n8n(booking_data)
        
        #Test de correo en Python
        src.notifications.enviar_confirmacion_cita(booking_data=booking_data)

        st.session_state.user_points += int(total)
        
        st.success("✅ ¡Reserva creada exitosamente!")
        
        st.markdown(f"""
        <div class='booking-code'>
            Tu código de cita:<br>
            {booking_code}
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"""
        📱 Te enviamos confirmación por email al {email}
        
        💡 **Guarda tu código de cita** - lo necesitarás para cancelar o cambiar tu cita.
        """)
        
        st.markdown(f"""
        <a href='{payment_url}' target='_blank'>
            <button style='background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
                           color: white; padding: 1rem 2rem; border: none; border-radius: 12px;
                           font-size: 1.1rem; font-weight: bold; cursor: pointer; width: 100%;
                           margin-top: 1rem;'>
                💳 Pagar Anticipo de ${deposit:.0f} MXN
            </button>
        </a>
        """, unsafe_allow_html=True)
        
        st.caption("Serás redirigido a Mercado Pago para completar el pago de forma segura")
        
        # Limpiar carrito y selecciones
        st.session_state.cart = []
        st.session_state.selected_date = None
        st.session_state.selected_slot = None

def render_manage_booking():
    """Vista para gestionar cita (cancelar, cambiar, ver estado)"""
    if st.button("← Volver al Inicio", key="back_to_home_manage"):
        st.session_state.current_view = 'home'
        st.rerun()
    
    st.markdown("## 🔍 Gestiona tu Cita")
    st.markdown("---")
    
    st.markdown("### Ingresa tu código de cita")
    booking_code = st.text_input(
        "Código de cita (ejemplo: BC-202501-A7K3M)",
        placeholder="BC-XXXXXX-XXXXX",
        key="booking_code_input"
    ).upper()
    
    if booking_code and len(booking_code) >= 10:
        booking = db.get_booking_by_code(booking_code)
        
        if not booking:
            st.error("❌ No encontramos una cita con ese código")
        else:
            # ========== MOSTRAR INFORMACIÓN DE LA CITA ==========
            st.success(f"""
            ### ✅ Cita encontrada
            
            **Nombre:** {booking['client_name']}  
            **Teléfono:** {booking['client_phone']}  
            **Email:** {booking['client_email']}  
            **Estado:** {booking['status'].upper()}
            """)
            
            # Mostrar detalles de servicios
            services = db.get_booking_services(booking['id'])
            
            st.markdown("#### 📋 Servicios reservados:")
            for service in services:
                st.caption(f"• {service['service_name']} - ${service['service_price']}")
            
            # Obtener depósito requerido
            required_deposit = db.get_required_deposit(booking['id'])
             # ← AGREGAR ESTA LÍNEA
            required_deposit = float(required_deposit) if required_deposit else 0
            # ← Y ESTA LÍNEA
            deposit_paid = float(booking['deposit_paid'])

            st.markdown(f"""
            #### 📅 Información de la cita:
            
            **Fecha:** {booking['date']}  
            **Hora:** {booking['start_time']} - {booking['end_time']}  
            **Total:** ${booking['total_price']} MXN  
            **Anticipo requerido:** ${required_deposit:.2f} MXN  
            **Anticipo pagado:** ${deposit_paid:.2f} MXN  
            **Pendiente:** ${required_deposit - deposit_paid:.2f} MXN
            """)
            
            st.markdown("---")
            
            # ========== SECCIÓN DE PAGO ==========
            st.markdown("#### 💳 Estado de Pago")
            
            # Si el depósito NO ha sido pagado
            if booking['deposit_paid'] == 0:
                st.warning(f"⏳ **Depósito pendiente: ${required_deposit} MXN**")
                
                # Botón para pagar
                if st.button("💳 Pagar Depósito Ahora", use_container_width=True, key="pay_deposit_now"):
                    st.session_state.current_view = 'pay_deposit'
                    st.session_state.current_booking_code = booking_code
                    st.session_state.required_deposit = required_deposit
                    st.rerun()
            
            # Si ya pagó el depósito
            elif booking['deposit_paid'] > 0:
                st.success(f"✅ **Depósito pagado: ${booking['deposit_paid']} MXN**")
                
                # Mostrar estado de pago en Mercado Pago si existe
                payments = db.get_payments_by_booking(booking_code)
                if payments:
                    payment = payments[0]
                    payment_status = {
                        'pending': '⏳ Pendiente',
                        'receipt_pending_verification': '📸 Comprobante cargado, esperando verificación',
                        'verified': '✅ Verificado',
                        'rejected': '❌ Rechazado'
                    }
                    st.info(f"Estado del pago: {payment_status.get(payment['payment_status'], payment['payment_status'])}")

            
            # ========== OPCIONES DE GESTIÓN ==========
            st.markdown("### Opciones de la cita")
            
            # ========== VALIDAR ESTADO DE LA CITA ==========
            if booking['status'].lower() == 'cancelled':
                st.warning("⚠️ Esta cita ha sido cancelada. No es posible realizar cambios.")
            else:
                # ========== OPCIONES DE GESTIÓN ==========
                st.markdown("### Opciones de la cita")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📸 Subir Comprobante de Pago", use_container_width=True, key="upload_receipt"):
                        st.session_state.current_view = 'upload_payment'
                        st.session_state.current_booking_code = booking_code
                        st.rerun()
                
                with col2:
                    if st.button("📅 Cambiar Fecha/Hora", use_container_width=True, key="reschedule"):
                        st.session_state.current_view = 'reschedule_booking'
                        st.session_state.current_booking_code = booking_code
                        st.rerun()
                
                with col3:
                    if st.button("❌ Cancelar Cita", use_container_width=True, key="cancel"):
                        st.session_state.current_view = 'cancel_booking'
                        st.session_state.current_booking_code = booking_code
                        st.rerun()

def render_pay_deposit():
    """Vista para pagar depósito de cita existente - Redirige a Mercado Pago"""
    booking_code = st.session_state.current_booking_code
    booking = db.get_booking_by_code(booking_code)
    required_deposit = st.session_state.get('required_deposit', 0)
    
    if not booking:
        st.error("Cita no encontrada")
        return
    
    if st.button("← Volver", key="back_to_manage_pay"):
        st.session_state.current_view = 'manage_booking'
        st.rerun()
    
    st.markdown("## 💳 Pagar Depósito")
    st.markdown(f"**Cita:** {booking_code}")
    st.markdown("---")
    
    # Mostrar información de la cita
    st.info(f"""
    **Cliente:** {booking['client_name']}
    **Monto a pagar:** ${required_deposit:.2f} MXN
    **Fecha de la cita:** {booking['date']}
    """)
    
    st.markdown("---")
    
    # Obtener servicios de la cita para la descripción
    services = db.get_booking_services(booking['id'])
    
    # Preparar datos para Mercado Pago (igual que en checkout)
    booking_data = {
        'booking_code': booking_code,
        'booking_id': booking['id'],
        'client': {
            'name': booking['client_name'],
            'email': booking['client_email'],
            'phone': booking['client_phone']
        },
        'services': [{'name': s['service_name'], 'price': float(s['service_price'])} for s in services],
        'appointment': {
            'date': str(booking['date']),
            'start_time': str(booking['start_time']),
            'end_time': str(booking['end_time'])
        },
        'payment': {
            'total': float(booking['total_price']),
            'deposit': float(required_deposit),
            'remaining': float(booking['total_price'] - required_deposit)
        }
    }
    
    # Crear preferencia de Mercado Pago
    payment_url = create_mercadopago_preference(booking_data)
    
    if payment_url:
        st.markdown("### 💳 Proceder al Pago")
        st.markdown(f"""
        Haz clic en el botón para ir a Mercado Pago y confirmar tu pago de **${required_deposit:.2f} MXN**
        """)
        
        # Botón personalizado hacia Mercado Pago (igual que en checkout)
        st.markdown(f"""
        <a href='{payment_url}' target='_blank'>
            <button style='background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
                           color: white; padding: 1rem 2rem; border: none; border-radius: 12px;
                           font-size: 1.1rem; font-weight: bold; cursor: pointer; width: 100%;
                           margin-top: 1rem;'>
                💳 Pagar ${required_deposit:.2f} MXN en Mercado Pago
            </button>
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("""
        **Después de pagar:**
        
        1. Recibirás confirmación en Mercado Pago
        2. Tu depósito será registrado automáticamente
        3. Recibirás confirmación por email
        4. En caso de dudas, ingresa tu código de cita en "Gestiona tu Cita"
        """)
    else:
        st.error("❌ No se pudo procesar el pago. Intenta más tarde.")




def render_upload_payment():
    """Vista para validar pago con número de operación de Mercado Pago"""
    booking_code = st.session_state.current_booking_code
    booking = db.get_booking_by_code(booking_code)
    
    if not booking:
        st.error("Cita no encontrada")
        return
    
    if st.button("← Volver", key="back_to_manage"):
        st.session_state.current_view = 'manage_booking'
        st.rerun()
    
    st.markdown("## 💳 Validar Pago - Mercado Pago")
    st.markdown(f"**Cita:** {booking_code}")
    st.markdown("---")
    
    st.info(f"""
    Para confirmar tu pago, ingresa el número de operación de Mercado Pago.
    
    **Monto a pagar:** ${booking['deposit_paid']} MXN
    
    ℹ️ El número de operación aparece en:
    - Tu comprobante de pago
    - Email de confirmación de Mercado Pago
    - Tu cuenta de Mercado Pago (en Mis compras)
    """)
    
    st.markdown("### 🔢 Número de Operación")
    
    operation_number = st.text_input(
        "Ingresa el número de operación",
        placeholder="Ejemplo: 12345678901",
        key="operation_number",
        help="Es el número que aparece en tu comprobante de pago de Mercado Pago"
    )
    
    if operation_number:
        st.markdown("---")
        
        if st.button("✅ Validar Pago", use_container_width=True, key="validate_payment"):
            with st.spinner("⏳ Validando pago con Mercado Pago..."):
                 # Obtener Access Token desde env
                try:
                    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
                except (KeyError, TypeError):
                    st.error("❌ Token de Mercado Pago no configurado. Contacta con soporte.")
                    return
                
                # Validar el número de operación con HTTP request
                # Pasar: numero de operación, booking_id, access_token
                is_valid, payment_data, error_message = db.validate_mercadopago_payment(
                    operation_number, 
                    booking_code,  # ← Usar booking['id'] como referencia
                    access_token    # ← Pasar access_token desde app.py
                )
                
                if is_valid:
                    st.success(f"""
                    ✅ ¡Pago Validado Exitosamente!
                    
                    **Número de operación:** {payment_data.get('operation_id')}
                    **Monto confirmado:** ${payment_data.get('amount')} MXN
                    **Estado:** {payment_data.get('status')}
                    **Fecha:** {payment_data.get('date')}
                    
                    Tu cita ha sido confirmada.
                    Te enviaremos los detalles por email.
                    """)
                    
                    # Registrar validación en base de datos
                    success_confirmation, confirmation_message = db.confirm_payment_with_operation(
                        booking_code,
                        operation_number,  # Usar payment_id de Mercado Pago
                        payment_data
                    )

                    if success_confirmation:
                        st.success(f"✅ {confirmation_message}")
                    else:
                        st.error(f"⚠️ Confirmación pendiente: {confirmation_message}")

                    if st.button("Volver al Inicio", key="back_after_validation"):
                        st.session_state.current_view = 'home'
                        st.rerun()
                
                else:  # ← ELSE CORRECTO: es para if is_valid
                    st.error(f"""
                    ❌ Error en la Validación
                    
                    {error_message}
                    
                    Por favor:
                    1. Verifica que el número de operación sea correcto
                    2. Asegúrate que el monto coincida
                    3. Si el problema persiste, contacta con soporte
                    """)
    
    else:  # ← ELSE CORRECTO: es para if operation_number
        st.warning("👆 Por favor ingresa el número de operación para validar tu pago")



def render_cancel_booking():
    """Vista para cancelar cita"""
    booking_code = st.session_state.current_booking_code
    booking = db.get_booking_by_code(booking_code)
    
    if not booking:
        st.error("Cita no encontrada")
        return
    
    if st.button("← Volver", key="back_cancel"):
        st.session_state.current_view = 'manage_booking'
        st.rerun()
    
    st.markdown("## ❌ Cancelar Cita")
    st.markdown(f"**Cita:** {booking_code}")
    st.markdown("---")
    
    st.warning(f"""
    ⚠️ **Advertencia:** Estás a punto de cancelar tu cita.
    
    **Fecha:** {booking['date']}  
    **Hora:** {booking['start_time']} - {booking['end_time']}
    """)
    
    reason = st.text_area(
        "¿Por qué deseas cancelar? (opcional)",
        placeholder="Cuéntanos el motivo de la cancelación",
        key="cancel_reason"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Confirmar Cancelación", use_container_width=True, key="confirm_cancel"):
            success, message = db.cancel_booking(booking_code, reason)

            if success:
                # Liberar el horario que quedó libre
                if booking:
                    success_schedule, msg_schedule = db.mark_schedule_available_by_date_time(
                        professional_id=booking['professional_id'],
                        date=booking['date'],
                        start_time=booking['start_time']
                    )
                    if not success_schedule:
                        st.warning(f"⚠️ Aviso al liberar horario: {msg_schedule}")
                
                # ========== NUEVO: Preparar datos para el correo ==========
                booking_data = {
                    'booking_code': booking_code,
                    'event': 'booking_cancelled',
                    'client': {
                        'name': booking.get('client_name', 'Cliente'),
                        'email': booking.get('client_email', ''),
                        'phone': booking.get('client_phone', '')
                    },
                    'appointment': {
                        'date': booking['date'],
                        'day': booking.get('day', ''),
                        'start_time': booking['start_time'],
                        'end_time': booking['end_time'],
                        'duration': booking.get('duration', '')
                    },
                    'professional': {
                        'id': booking['professional_id'],
                        'name': booking.get('professional_name', '')
                    },
                    'payment': {
                        'deposit': float(booking.get('deposit_amount', 0))
                    },
                    'cancelacion_razon': reason
                }
                
                # Enviar correo de cancelación
                email_sent = src.notifications.enviar_cancelacion_cita(
                    booking_data=booking_data,
                    razon_cancelacion=reason
                )
                
                # Mostrar resultado
                if email_sent:
                    st.success(f"""
                    ✅ {message}
                    
                    ✉️ Confirmación enviada por correo
                    Política de reembolso: Se procesará en 5-7 días hábiles.
                    """)
                else:
                    st.success(f"""
                    ✅ {message}
                    
                    ⚠️ No se pudo enviar el correo, pero la cita fue cancelada.
                    Política de reembolso: Se procesará en 5-7 días hábiles.
                    """)
                
                # ========== FIN: Envío de correo ==========
                
                if st.button("Volver al Inicio", key="back_home_cancel"):
                    st.session_state.current_view = 'home'
                    st.rerun()
            else:
                st.error(f"❌ Error: {message}")
    
    with col2:
        if st.button("❌ No Cancelar", use_container_width=True, key="dont_cancel"):
            st.session_state.current_view = 'manage_booking'
            st.rerun()

def render_reschedule_booking():
    """Vista para cambiar fecha/hora de cita"""
    booking_code = st.session_state.current_booking_code
    booking = db.get_booking_by_code(booking_code)
    
    if not booking:
        st.error("Cita no encontrada")
        return
    
    if st.button("← Volver", key="back_reschedule"):
        st.session_state.current_view = 'manage_booking'
        st.rerun()
    
    st.markdown("## 📅 Cambiar Fecha/Hora de tu Cita")
    st.markdown(f"**Cita actual:** {booking_code}")
    st.markdown("---")
    
    st.info(f"""
    **Fecha actual:** {booking['date']}  
    **Hora actual:** {booking['start_time']} - {booking['end_time']}
    """)
    
    st.markdown("### Selecciona nueva fecha y hora")
    
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(0, 30)]
    
    cols = st.columns(3)
    selected_new_date = None
    
    for idx, date in enumerate(dates[:9]):
        weekday = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][date.weekday()]
        
        with cols[idx % 3]:
            if st.button(
                f"**{date.strftime('%d/%m')}**\n{weekday}",
                key=f"new_date_{date}",
                use_container_width=True
            ):
                selected_new_date = str(date)
                st.session_state.temp_new_date = selected_new_date
    
    if 'temp_new_date' in st.session_state:
        new_date = st.session_state.temp_new_date
        st.markdown(f"**Fecha seleccionada:** {new_date}")
        
        # OBTENER HORARIOS DISPONIBLES PARA LA NUEVA FECHA
        st.markdown("#### ⏰ Horarios disponibles:")
        
        # Obtener datos de la cita actual
        booking = db.get_booking_by_code(booking_code)
        
        if booking:
            # Obtener profesional de la cita actual
            professional_id = booking['professional_id']
            
            # Obtener citas confirmadas del profesional para esa fecha (EXCLUIR la cita actual)
            booked_slots = db.get_professional_bookings_by_date(professional_id, new_date)
            
            # Filtrar para excluir la cita actual del usuario
            booked_slots = [slot for slot in booked_slots if slot['booking_code'] != booking_code]
            
            # Obtener horarios disponibles del profesional
            available_times = db.get_professional_schedule(professional_id, new_date)
            
            if available_times:
                # Filtrar horarios que no tengan conflicto con otras citas
                filtered_times = []
                
                #Obtener datos del cliente
                client_name = booking['client_name']
                client_email = booking['client_email']

                # Obtener duración de la cita actual
                current_start_h, current_start_m = map(int, booking['start_time'].split(':'))
                current_end_h, current_end_m = map(int, booking['end_time'].split(':'))
                current_start_minutes = current_start_h * 60 + current_start_m
                current_end_minutes = current_end_h * 60 + current_end_m
                duration = current_end_minutes - current_start_minutes
                
                for time_slot in available_times:
                    # Convertir hora propuesta a minutos
                    slot_h, slot_m = map(int, time_slot.split(':'))
                    slot_start_minutes = slot_h * 60 + slot_m
                    slot_end_minutes = slot_start_minutes + duration
                    
                    # Validar que no haya solapamiento con otras citas
                    is_available = True
                    for booked in booked_slots:
                        booked_start = booked['start_time']
                        booked_end = booked['end_time']
                        
                        # Convertir a minutos para comparación
                        booked_start_h, booked_start_m = map(int, booked_start.split(':'))
                        booked_start_minutes = booked_start_h * 60 + booked_start_m
                        
                        booked_end_h, booked_end_m = map(int, booked_end.split(':'))
                        booked_end_minutes = booked_end_h * 60 + booked_end_m
                        
                        # Verificar solapamiento
                        if (slot_start_minutes < booked_end_minutes) and (slot_end_minutes > booked_start_minutes):
                            is_available = False
                            break
                    
                    if is_available:
                        filtered_times.append(time_slot)
                
                if filtered_times:
                    st.success(f"✅ {len(filtered_times)} horarios disponibles para {new_date}")
                    
                    # Mostrar horarios en columnas de 4
                    cols = st.columns(4)
                    
                    if 'selected_new_time' not in st.session_state:
                        st.session_state.selected_new_time = None
                    
                    for idx, time_slot in enumerate(filtered_times):
                        with cols[idx % 4]:
                            # Cambiar color si está seleccionado
                            is_selected = st.session_state.selected_new_time == time_slot
                            button_color = "🟢" if is_selected else "⏰"
                            
                            if st.button(
                                f"{button_color} {time_slot}",
                                key=f"new_time_slot_{time_slot}",
                                use_container_width=True
                            ):
                                st.session_state.selected_new_time = time_slot
                                st.rerun()
                    
                    # Mostrar hora seleccionada
                    if st.session_state.selected_new_time:
                        st.info(f"✅ Hora seleccionada: **{st.session_state.selected_new_time}**")
                    else:
                        st.warning("👆 Selecciona un horario disponible")
                    
                    st.markdown("---")
                    
                    reason = st.text_area(
                        "Motivo del cambio (opcional)",
                        placeholder="Cuéntanos por qué necesitas cambiar la fecha",
                        key="reschedule_reason"
                    )
                    
                    if st.button("✅ Realizar Cambio", use_container_width=True, key="confirm_reschedule"):
                        if st.session_state.selected_new_time:
                            new_time = st.session_state.selected_new_time
                            
                            # Actualizar la cita directamente en la BD
                            success, message = db.update_booking_date_time(
                                booking_code, new_date, new_time, reason
                            )

                            if success:
                                st.success(f"""
                                ✅ {message}
                                
                                Tu cita ha sido actualizada correctamente.
                                📅 Nueva fecha: {new_date}
                                🕐 Nueva hora: {new_time}
                                """)
                                src.notifications.enviar_confirmacion_cambio(client_name,client_email,booking_code,new_date,new_time,reason)

                                # Limpiar states
                                st.session_state.selected_new_time = None
                                st.session_state.temp_new_date = None
                                
                                if st.button("Volver al Inicio", key="home_reschedule"):
                                    st.session_state.current_view = 'home'
                                    st.rerun()
                            else:
                                st.error(f"❌ Error: {message}")
                        else:
                            st.error("⚠️ Por favor selecciona una hora disponible")
                else:
                    st.error(f"""
                    ❌ No hay horarios disponibles para {new_date}
                    
                    Por favor:
                    1. Selecciona otra fecha
                    2. O contacta directamente con nosotros
                    """)
                    
                    if st.button("← Volver a seleccionar fecha", key="back_date_selection"):
                        st.session_state.temp_new_date = None
                        st.rerun()
            
            else:
                st.error(f"""
                ❌ No hay horarios disponibles para {new_date}
                
                Por favor:
                1. Selecciona otra fecha
                2. O contacta directamente con nosotros
                """)
                
                if st.button("← Volver a seleccionar fecha", key="back_date_selection_2"):
                    st.session_state.temp_new_date = None
                    st.rerun()
        
        else:
            st.error("No se encontró la información de tu cita")




# ==================== MAIN ====================

def main():
    view = st.session_state.current_view
    
    if view == 'home':
        render_home()
    elif view == 'services':
        render_services()
    elif view == 'cart':
        render_cart()
    elif view == 'calendar':
        render_calendar()
    elif view == 'checkout':
        render_checkout()
    elif view == 'manage_booking':
        render_manage_booking()
    elif view == 'upload_payment':
        render_upload_payment()
    elif view == 'cancel_booking':
        render_cancel_booking()
    elif view == 'reschedule_booking':
        render_reschedule_booking()
    elif st.session_state.current_view == 'pay_deposit':
        render_pay_deposit()
    
    # Botón de chat flotante
    st.markdown("""
    <div style='position: fixed; bottom: 20px; right: 20px; z-index: 999;'>
        <div style='background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%);
                    color: white; width: 60px; height: 60px; border-radius: 50%;
                    display: flex; align-items: center; justify-content: center;
                    box-shadow: 0 4px 12px rgba(236,72,153,0.5); cursor: pointer;
                    font-size: 24px;'>
            💬
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()