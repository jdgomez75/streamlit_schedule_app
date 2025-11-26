import streamlit as st
import requests
from datetime import datetime, timedelta
from database import Database
import json
import os
from dotenv import load_dotenv

# Configuración de la página
st.set_page_config(
    page_title="Bella Clinic - Reservas",
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

# Inicializar base de datos
@st.cache_resource
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
            st.success("✅ Confirmación enviada por WhatsApp")
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
    ACCESS_TOKEN = st.secrets["mercadopago"]["ACCESS_TOKEN"]
    
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

# ==================== VISTAS ====================

def render_home():
    """Página de inicio"""
    st.markdown("""
    <div class='clinic-header'>
        <h1>✨ Bella Clinic</h1>
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
            st.info("📱 WhatsApp: +52 55 1234 5678\n📧 Email: info@bellaclinic.com")

def render_services():
    """Vista de servicios con categorías como botones"""
    if st.button("← Volver", key="back_to_home"):
        st.session_state.current_view = 'home'
        st.rerun()
    
    st.markdown("## 💅 Servicios Disponibles")
    st.markdown("---")
    
    # Inicializar session state para categoría seleccionada
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = None
    
    services = db.get_services()
    
    if not services:
        st.warning("No hay servicios disponibles")
        return
    
    # Agrupar servicios por categoría
    categories = {}
    for service in services:
        cat = service.get('category', 'General')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(service)
    
    # Mostrar botones de categorías
    st.markdown("### 📁 Selecciona una Categoría")
    cols = st.columns(len(categories))
    
    for idx, (category, category_services) in enumerate(sorted(categories.items())):
        with cols[idx]:
            num_services = len(category_services)
            if st.button(
                f"📍 {category}\n({num_services} servicios)",
                key=f"category_{category}",
                use_container_width=True
            ):
                st.session_state.selected_category = category
                st.rerun()
    
    # Mostrar servicios de la categoría seleccionada
    if st.session_state.selected_category:
        selected_cat = st.session_state.selected_category
        category_services = categories.get(selected_cat, [])
        
        st.markdown(f"### 💅 Servicios en {selected_cat}")
        st.markdown("---")
        
        # Mostrar servicios en columnas de 2
        cols = st.columns(2)
        
        for idx, service in enumerate(category_services):
            with cols[idx % 2]:
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
                
                if st.button(
                    f"✅ Agregar a tu cita",
                    key=f"add_{service['id']}",
                    use_container_width=True
                ):
                    add_to_cart(service)
                    st.success(f"✅ {service['name']} agregado a tu cita")
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

def render_cart():
    """Vista del carrito"""
    if st.button("← Volver", key="back_to_services"):
        st.session_state.current_view = 'services'
        st.rerun()
    
    st.markdown("## 🛒 Tu Carrito")
    st.markdown("---")
    
    if not st.session_state.cart:
        st.info("Tu carrito está vacío")
        return
    
    for service in st.session_state.cart:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{service['name']}** - ${service['price']} | ⏱️ {service['duration']} min")
        with col3:
            if st.button("❌ Eliminar", key=f"remove_{service['id']}", use_container_width=True):
                remove_from_cart(service['id'])
    
    st.markdown("---")
    st.markdown(f"### Total: ${get_total_price()} MXN")
    st.markdown(f"### Duración total: {get_total_duration()} minutos")
    st.markdown(f"### Anticipo requerido: ${calculate_deposit()} MXN")
    
    if st.button("📅 Seleccionar Fecha y Hora", use_container_width=True, key="proceed_calendar", type="primary"):
        st.session_state.current_view = 'calendar'
        st.rerun()

def render_calendar():
    """Vista de selección de fecha y hora"""
    if st.button("← Volver", key="back_to_cart"):
        st.session_state.current_view = 'cart'
        st.rerun()
    
    st.markdown("## 📅 Selecciona tu Fecha y Hora")
    st.markdown("---")
    
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(1, 30)]
    
    st.markdown("### Fechas disponibles")
    cols = st.columns(3)
    
    for idx, date in enumerate(dates[:9]):
        weekday = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'][date.weekday()]
        date_info = {
            'date': str(date),
            'day': date.strftime('%d/%m'),
            'weekday': weekday
        }
        
        with cols[idx % 3]:
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
            cols = st.columns(3)
            for idx, slot in enumerate(slots[:9]):
                with cols[idx % 3]:
                    prof_name = slot['professionals'][0]['name']
                    button_key = f"slot_{idx}_{slot['start_time']}"
                    if st.button(
                        f"**{slot['start_time']} - {slot['end_time']}**\n\n👤 {prof_name}", 
                        key=button_key,
                        use_container_width=True
                    ):
                        st.session_state.selected_slot = {
                            'start_time': slot['start_time'],
                            'end_time': slot['end_time'],
                            'duration': slot['duration'],
                            'type': slot['type'],
                            'professionals': slot['professionals'],
                            'description': slot.get('description', '')
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
    
    name = st.text_input("Nombre completo *", placeholder="María García", key=f"client_name_{button_key}")
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
        booking_id, booking_code = db.create_booking(
            client_name=name,
            client_phone=phone,
            client_email=email,
            date=st.session_state.selected_date['date'],
            start_time=st.session_state.selected_slot['start_time'],
            end_time=st.session_state.selected_slot['end_time'],
            professional_id=prof.get('id'),
            services=st.session_state.cart,
            total_price=total,
            deposit_paid=deposit
        )

        # Guardar código de cita en session
        st.session_state.current_booking_code = booking_code
        st.session_state.last_booking_id = booking_id
        
        # Crear registro de pago
        db.create_payment(booking_code, booking_id, deposit, 'deposit')
        
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
            'services': [{'name': s['name'], 'price': s['price']} for s in st.session_state.cart],
            'professional': {
                'id': prof['id'],
                'name': prof['name']
            },
            'payment': {
                'total': total,
                'deposit': deposit,
                'remaining': total - deposit
            }
        }
        
        payment_url = create_mercadopago_preference(booking_data)
        send_webhook_to_n8n(booking_data)
        
        st.session_state.user_points += int(total)
        
        st.success("✅ ¡Reserva creada exitosamente!")
        
        st.markdown(f"""
        <div class='booking-code'>
            Tu código de cita:<br>
            {booking_code}
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"""
        📱 Te enviamos confirmación por WhatsApp al {phone}
        
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
            
            st.markdown(f"""
            #### 📅 Información de la cita:
            
            **Fecha:** {booking['date']}  
            **Hora:** {booking['start_time']} - {booking['end_time']}  
            **Total:** ${booking['total_price']} MXN  
            **Anticipo pagado:** ${booking['deposit_paid']} MXN  
            **Pendiente:** ${booking['total_price'] - booking['deposit_paid']} MXN
            """)
            
            # Mostrar estado de pago
            payment = db.get_payments_by_booking(booking_code)
            if payment:
                st.markdown(f"#### 💳 Estado de pago:")
                payment_status = {
                    'pending': '⏳ Pendiente',
                    'receipt_pending_verification': '📸 Comprobante cargado, esperando verificación',
                    'verified': '✅ Verificado',
                    'rejected': '❌ Rechazado'
                }
                st.info(f"Estado: {payment_status.get(payment['payment_status'], payment['payment_status'])}")
            
            st.markdown("---")
            
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
                 # Obtener Access Token desde secrets
                try:
                    access_token = st.secrets["mercadopago"]["ACCESS_TOKEN"]
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
                    Te enviaremos los detalles por WhatsApp.
                    """)
                    
                    # Registrar validación en base de datos
                    db.confirm_payment_with_operation(
                        booking_code, 
                        operation_number,
                        payment_data
                    )
                    
                    if st.button("Volver al Inicio", key="back_after_validation"):
                        st.session_state.current_view = 'home'
                        st.rerun()
                
                else:
                    st.error(f"""
                    ❌ Error en la Validación
                    
                    {error_message}
                    
                    Por favor:
                    1. Verifica que el número de operación sea correcto
                    2. Asegúrate que el monto coincida
                    3. Si el problema persiste, contacta con soporte
                    """)
    
    else:
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
                
                st.success(f"""
                ✅ {message}
                
                Te enviaremos una confirmación por WhatsApp.
                Política de reembolso: Se procesará en 5-7 días hábiles.
                """)
                
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
    dates = [today + timedelta(days=i) for i in range(1, 30)]
    
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