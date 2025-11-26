import psycopg2
from psycopg2 import sql
import uuid
from datetime import datetime, time, date
from contextlib import contextmanager
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Database:
    def __init__(self, database_url=None):
        """
        Inicializa la conexión a PostgreSQL
        
        Args:
            database_url (str): URL de conexión a PostgreSQL
                                Si no se proporciona, usa DATABASE_URL del .env
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL no configurada. "
                "Configura la variable de entorno o pasa database_url como parámetro"
            )
    
    def _convert_time_to_string(self, value):
        """Convierte objetos datetime.time a strings HH:MM"""
        if value is None:
            return None
        if isinstance(value, time):
            return value.strftime('%H:%M')
        return str(value)
    
    def _convert_date_to_string(self, value):
        """Convierte objetos datetime.date a strings YYYY-MM-DD"""
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        return str(value)
    
    def _row_to_dict(self, cursor, row):
        """Convierte una fila de PostgreSQL a diccionario, convirtiendo tipos especiales"""
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
        
        # Convertir tiempos y fechas
        for key, value in result.items():
            if isinstance(value, time):
                result[key] = self._convert_time_to_string(value)
            elif isinstance(value, date) and not isinstance(value, datetime):
                result[key] = self._convert_date_to_string(value)
        
        return result
    
    @contextmanager
    def get_connection(self):
        """Context manager para manejo seguro de conexiones a PostgreSQL"""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    # ==================== MÉTODOS DE SERVICIOS ====================
    
    def add_service(self, name, description, price, duration, deposit=200, category=None):
        """Agrega un nuevo servicio"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO services (name, description, price, duration, deposit, category)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (name, description, price, duration, deposit, category))
            return cursor.fetchone()[0]
    
    def get_services(self):
        """Obtiene todos los servicios activos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM services WHERE active = TRUE ORDER BY category, name')
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def get_service_by_id(self, service_id):
        """Obtiene un servicio por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM services WHERE id = %s', (service_id,))
            row = cursor.fetchone()
            
            return self._row_to_dict(cursor, row) if row else None
    
    # ==================== MÉTODOS DE PROFESIONALES ====================
    
    def add_professional(self, name, email=None, phone=None, specialization=None):
        """Agrega un nuevo profesional"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO professionals (name, email, phone, specialization)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (name, email, phone, specialization))
            return cursor.fetchone()[0]
    
    def get_professional_by_id(self, prof_id):
        """Obtiene profesional por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM professionals WHERE id = %s', (prof_id,))
            row = cursor.fetchone()
            
            return self._row_to_dict(cursor, row) if row else None
    
    def get_professionals_for_service(self, service_id):
        """Obtiene profesionales que pueden hacer un servicio"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT professional_id FROM professional_services
                WHERE service_id = %s
            ''', (service_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def add_professional_service(self, professional_id, service_id):
        """Asigna un servicio a un profesional"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO professional_services (professional_id, service_id)
                    VALUES (%s, %s)
                ''', (professional_id, service_id))
                return True
            except psycopg2.IntegrityError:
                return False
    
    # ==================== MÉTODOS DE HORARIOS ====================
    
    def add_schedule(self, professional_id, date, start_time):
        """Agrega un slot de horario disponible"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (professional_id, date, start_time, available)
                VALUES (%s, %s, %s, TRUE)
                RETURNING id
            ''', (professional_id, date, start_time))
            return cursor.fetchone()[0]
    
    def get_professional_bookings_by_date(self, professional_id, date):
        """Obtiene todas las citas confirmadas de un profesional para una fecha específica"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, booking_code, date, start_time, end_time, status
                FROM bookings
                WHERE professional_id = %s AND date = %s AND status IN ('confirmed', 'pending')
                ORDER BY start_time
            ''', (professional_id, date))
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def get_daily_bookings(self, date_str):
        """
        Obtiene todas las citas de un día específico
        
        Parámetros:
            date_str (str): Fecha en formato 'YYYY-MM-DD'
        
        Retorna:
            list: Lista de citas del día ordenadas por hora
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    b.*,
                    p.name as professional_name
                FROM bookings b
                LEFT JOIN professionals p ON b.professional_id = p.id
                WHERE b.date = %s
                ORDER BY b.start_time
            ''', (date_str,))
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def get_professional_schedule(self, professional_id, date):
        """Obtiene horarios disponibles para un profesional en una fecha"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT start_time FROM schedules
                WHERE professional_id = %s AND date = %s AND available = TRUE
                ORDER BY start_time
            ''', (professional_id, date))
            
            # Convertir a strings
            return [self._convert_time_to_string(row[0]) for row in cursor.fetchall()]
    
    def mark_schedule_unavailable_by_date_time(self, professional_id, date, start_time):
        """
        Marca un horario como ocupado buscando por fecha y hora
        
        Parámetros:
            professional_id (int): ID del profesional
            date (str): Fecha 'YYYY-MM-DD'
            start_time (str): Hora 'HH:MM'
        
        Retorna:
            (bool, str): (éxito, mensaje)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE schedules 
                    SET available = FALSE
                    WHERE professional_id = %s AND date = %s AND start_time = %s
                ''', (professional_id, date, start_time))
                conn.commit()
                
                if cursor.rowcount > 0:
                    return True, "✅ Horario marcado como ocupado"
                else:
                    return False, "⚠️ No se encontró el horario"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def mark_schedule_available_by_date_time(self, professional_id, date, start_time):
        """
        Marca un horario como disponible (cuando se cancela o cambia una cita)
        
        Parámetros:
            professional_id (int): ID del profesional
            date (str): Fecha 'YYYY-MM-DD'
            start_time (str): Hora 'HH:MM'
        
        Retorna:
            (bool, str): (éxito, mensaje)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE schedules 
                    SET available = TRUE
                    WHERE professional_id = %s AND date = %s AND start_time = %s
                ''', (professional_id, date, start_time))
                conn.commit()
                
                if cursor.rowcount > 0:
                    return True, "✅ Horario liberado"
                else:
                    return False, "⚠️ No se encontró el horario"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def get_professional_schedules(self, professional_id, start_date=None, end_date=None):
        """
        Obtiene todos los horarios de un profesional en un rango de fechas
        
        Parámetros:
            professional_id (int): ID del profesional
            start_date (str): Fecha inicio (opcional, formato 'YYYY-MM-DD')
            end_date (str): Fecha fin (opcional, formato 'YYYY-MM-DD')
        
        Retorna:
            list: Lista de horarios disponibles
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM schedules WHERE professional_id = %s"
            params = [professional_id]
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            query += " ORDER BY date, start_time"
            
            cursor.execute(query, params)
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def delete_professional_schedules(self, professional_id, start_date=None, end_date=None):
        """
        Elimina horarios de un profesional
        
        Parámetros:
            professional_id (int): ID del profesional
            start_date (str): Fecha inicio (opcional)
            end_date (str): Fecha fin (opcional)
        
        Retorna:
            (bool, str): (éxito, mensaje)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "DELETE FROM schedules WHERE professional_id = %s"
                params = [professional_id]
                
                if start_date:
                    query += " AND date >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date <= %s"
                    params.append(end_date)
                
                cursor.execute(query, params)
                conn.commit()
                
                deleted = cursor.rowcount
                return True, f"✅ {deleted} horarios eliminados"
        
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def get_available_slots(self, professional_id, date, service_duration=30):
        """
        Obtiene los slots disponibles de un profesional para una fecha específica
        
        Parámetros:
            professional_id (int): ID del profesional
            date (str): Fecha 'YYYY-MM-DD'
            service_duration (int): Duración del servicio en minutos
        
        Retorna:
            list: Lista de horas disponibles
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener horarios del profesional para esa fecha
            cursor.execute('''
                SELECT * FROM schedules
                WHERE professional_id = %s AND date = %s AND available = TRUE
                ORDER BY start_time
            ''', (professional_id, date))
            
            available_slots = []
            schedules = cursor.fetchall()
            
            for schedule in schedules:
                schedule_dict = self._row_to_dict(cursor, schedule)
                start_time = schedule_dict['start_time']
                available_slots.append({
                    'date': date,
                    'time': start_time,
                    'professional_id': professional_id,
                    'available': True
                })
            
            return available_slots
    
    def mark_schedule_unavailable(self, schedule_id):
        """
        Marca un horario como no disponible (porque hay una cita)
        
        Parámetros:
            schedule_id (int): ID del horario
        
        Retorna:
            (bool, str): (éxito, mensaje)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE schedules SET available = FALSE
                    WHERE id = %s
                ''', (schedule_id,))
                conn.commit()
                return True, "✅ Horario marcado como no disponible"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def get_schedule_statistics(self, professional_id, start_date, end_date):
        """
        Obtiene estadísticas de horarios disponibles
        
        Parámetros:
            professional_id (int): ID del profesional
            start_date (str): Fecha inicio 'YYYY-MM-DD'
            end_date (str): Fecha fin 'YYYY-MM-DD'
        
        Retorna:
            dict: Estadísticas de disponibilidad
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de horarios
            cursor.execute('''
                SELECT COUNT(*) as total FROM schedules
                WHERE professional_id = %s AND date >= %s AND date <= %s
            ''', (professional_id, start_date, end_date))
            total = cursor.fetchone()[0]
            
            # Horarios disponibles
            cursor.execute('''
                SELECT COUNT(*) as available FROM schedules
                WHERE professional_id = %s AND date >= %s AND date <= %s AND available = TRUE
            ''', (professional_id, start_date, end_date))
            available = cursor.fetchone()[0]
            
            # Horarios ocupados
            occupied = total - available
            
            return {
                'total': total,
                'available': available,
                'occupied': occupied,
                'utilization_rate': (occupied / total * 100) if total > 0 else 0
            }
    
    # ==================== MÉTODOS DE CITAS ====================
    
    def create_booking(self, client_name, client_phone, client_email, date, start_time, 
                      end_time, professional_id, total_price, deposit_paid=0, services=None):
        """
        Crea una nueva cita
        
        Parámetros:
            client_name (str): Nombre del cliente
            client_phone (str): Teléfono del cliente
            client_email (str): Email del cliente
            date (str): Fecha 'YYYY-MM-DD'
            start_time (str): Hora inicio 'HH:MM'
            end_time (str): Hora fin 'HH:MM'
            professional_id (int): ID del profesional
            total_price (float): Precio total
            deposit_paid (float): Anticipo pagado
            services (list): Lista de servicios (dicts con 'id' y 'name')
        
        Retorna:
            (bool, str): (éxito, código de cita o mensaje de error)
        """
        try:
            booking_code = f"BC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insertar cita
                cursor.execute('''
                    INSERT INTO bookings 
                    (booking_code, client_name, client_phone, client_email, date, start_time, 
                     end_time, professional_id, total_price, deposit_paid, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                    RETURNING id
                ''', (booking_code, client_name, client_phone, client_email, date, start_time,
                      end_time, professional_id, total_price, deposit_paid))
                
                booking_id = cursor.fetchone()[0]
                
                # Insertar servicios si se proporcionan
                if services:
                    for service in services:
                        cursor.execute('''
                            INSERT INTO booking_services 
                            (booking_id, service_id, service_name, service_price)
                            VALUES (%s, %s, %s, %s)
                        ''', (booking_id, service['id'], service['name'], service['price']))
                
                conn.commit()
                return True, booking_code
        
        except Exception as e:
            return False, f"❌ Error al crear cita: {str(e)}"
    
    def get_booking_by_code(self, booking_code):
        """Obtiene una cita por su código"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bookings WHERE booking_code = %s', (booking_code,))
            row = cursor.fetchone()
            
            return self._row_to_dict(cursor, row) if row else None
    
    def get_booking_services(self, booking_id):
        """Obtiene los servicios de una cita"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM booking_services WHERE booking_id = %s
            ''', (booking_id,))
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def update_booking_status(self, booking_code, status):
        """Actualiza el estado de una cita"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE bookings 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                ''', (status, booking_code))
                conn.commit()
                
                if cursor.rowcount > 0:
                    return True, f"✅ Cita actualizada a {status}"
                else:
                    return False, "⚠️ Cita no encontrada"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def cancel_booking(self, booking_code, reason=None):
        """Cancela una cita"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener cita
                cursor.execute('''
                    SELECT * FROM bookings WHERE booking_code = %s
                ''', (booking_code,))
                
                row = cursor.fetchone()
                if not row:
                    return False, "⚠️ Cita no encontrada"
                
                booking = self._row_to_dict(cursor, row)
                
                # Actualizar estado a 'cancelled'
                cursor.execute('''
                    UPDATE bookings 
                    SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                ''', (booking_code,))
                
                # Registrar el cambio
                cursor.execute('''
                    INSERT INTO booking_changes 
                    (booking_code, booking_id, change_type, original_date, original_time, reason, status)
                    VALUES (%s, %s, 'cancellation', %s, %s, %s, 'completed')
                ''', (booking_code, booking['id'], booking['date'], booking['start_time'], reason))
                
                # Liberar horario
                self.mark_schedule_available_by_date_time(
                    booking['professional_id'],
                    str(booking['date']),
                    booking['start_time']
                )
                
                conn.commit()
                return True, "✅ Cita cancelada"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def update_booking_date_time(self, booking_code, new_date, new_time, reason=None):
        """Reprograma una cita"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener cita actual
                cursor.execute('''
                    SELECT * FROM bookings WHERE booking_code = %s
                ''', (booking_code,))
                
                row = cursor.fetchone()
                if not row:
                    return False, "⚠️ Cita no encontrada"
                
                booking = self._row_to_dict(cursor, row)
                
                # Liberar horario antiguo
                self.mark_schedule_available_by_date_time(
                    booking['professional_id'],
                    str(booking['date']),
                    booking['start_time']
                )
                
                # Actualizar cita
                cursor.execute('''
                    UPDATE bookings 
                    SET date = %s, start_time = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                ''', (new_date, new_time, booking_code))
                
                # Registrar cambio
                cursor.execute('''
                    INSERT INTO booking_changes 
                    (booking_code, booking_id, change_type, original_date, original_time, 
                     new_date, new_time, reason, status)
                    VALUES (%s, %s, 'reschedule', %s, %s, %s, %s, %s, 'completed')
                ''', (booking_code, booking['id'], booking['date'], booking['start_time'], 
                      new_date, new_time, reason))
                
                # Marcar nuevo horario como ocupado
                self.mark_schedule_unavailable_by_date_time(
                    booking['professional_id'],
                    new_date,
                    new_time
                )
                
                conn.commit()
                return True, "✅ Cita reprogramada"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    # ==================== MÉTODOS DE PAGOS ====================
    
    def create_payment(self, booking_code, booking_id, amount, payment_method='deposit', payment_status='pending'):
        """Crea un registro de pago"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments 
                    (booking_code, booking_id, amount, payment_method, payment_status)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (booking_code, booking_id, amount, payment_method, payment_status))
                
                payment_id = cursor.fetchone()[0]
                conn.commit()
                return True, payment_id
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def update_payment_status(self, payment_id, payment_status):
        """Actualiza el estado de un pago"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET payment_status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (payment_status, payment_id))
                conn.commit()
                return True, "✅ Pago actualizado"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def get_payments_by_booking(self, booking_code):
        """Obtiene todos los pagos de una cita"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM payments WHERE booking_code = %s ORDER BY created_at DESC
            ''', (booking_code,))
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def update_deposit_paid(self, booking_code, deposit_amount):
        """Actualiza el anticipo pagado de una cita"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE bookings 
                    SET deposit_paid = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                ''', (deposit_amount, booking_code))
                conn.commit()
                return True, "✅ Anticipo registrado"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def upload_payment_receipt(self, booking_code, receipt_path):
        """Registra un comprobante de pago"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET receipt_image_path = %s, receipt_uploaded_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                ''', (receipt_path, booking_code))
                conn.commit()
                return True, "✅ Comprobante registrado"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def verify_payment(self, payment_id):
        """Marca un pago como verificado"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET verified = TRUE, payment_status = 'verified'
                    WHERE id = %s
                ''', (payment_id,))
                conn.commit()
                return True, "✅ Pago verificado"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    # ==================== MÉTODOS DE REPORTES ====================
    
    def get_weekly_bookings(self, professional_id, start_date):
        """Obtiene las citas de una semana"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bookings 
                WHERE professional_id = %s 
                AND date >= %s 
                AND date < (date %s + INTERVAL '7 days')
                ORDER BY date, start_time
            ''', (professional_id, start_date, start_date))
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    def get_booking_statistics(self, start_date, end_date):
        """Obtiene estadísticas de citas en un rango de fechas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_bookings,
                    SUM(total_price) as total_revenue,
                    SUM(deposit_paid) as total_deposits,
                    COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled
                FROM bookings
                WHERE date >= %s AND date <= %s
            ''', (start_date, end_date))
            
            row = cursor.fetchone()
            return self._row_to_dict(cursor, row) if row else None
    
    def create_professional_schedules(self, professional_id, start_date, end_date, 
                                     start_time, end_time, days_of_week):
        """
        Crea horarios para un profesional en un rango de fechas y días de la semana
        
        Parámetros:
            professional_id (int): ID del profesional
            start_date (str): Fecha inicio 'YYYY-MM-DD'
            end_date (str): Fecha fin 'YYYY-MM-DD'
            start_time (str): Hora inicio 'HH:MM'
            end_time (str): Hora fin 'HH:MM'
            days_of_week (list): Lista de días ['Monday', 'Tuesday', ...]
        
        Retorna:
            (bool, str): (éxito, mensaje)
        """
        try:
            from datetime import datetime, timedelta
            
            # Convertir strings a dates
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Mapeo de nombres de días español → número (0=Lunes, 6=Domingo)
            day_map = {
                # Español
                'Lunes': 0,
                'Martes': 1,
                'Miércoles': 2,
                'Jueves': 3,
                'Viernes': 4,
                'Sábado': 5,
                'Domingo': 6,
                # Inglés
                'Monday': 0,
                'Tuesday': 1,
                'Wednesday': 2,
                'Thursday': 3,
                'Friday': 4,
                'Saturday': 5,
                'Sunday': 6,
                # Abreviaturas español
                'Lun': 0,
                'Mar': 1,
                'Mié': 2,
                'Jue': 3,
                'Vie': 4,
                'Sab': 5,
                'Dom': 6,
                # Números como strings
                '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6
            }
            
            # Obtener números de días - convertir a string si es necesario
            day_numbers = []
            for day in days_of_week:
                day_str = str(day).strip()  # Convertir a string y eliminar espacios
                if day_str in day_map:
                    day_numbers.append(day_map[day_str])
                else:
                    # Intentar encontrar coincidencia parcial
                    for key, val in day_map.items():
                        if day_str.lower() in key.lower() or key.lower() in day_str.lower():
                            day_numbers.append(val)
                            break
            
            # Remover duplicados y ordenar
            day_numbers = sorted(list(set(day_numbers)))
            
            if not day_numbers:
                # Debug: mostrar qué se recibió
                return False, f"❌ No se especificaron días válidos. Recibido: {days_of_week}"
            
            # Generar fechas y crear horarios
            current = start
            schedules_created = 0
            conn = None
            
            try:
                # Conectar directamente (no usar context manager)
                conn = psycopg2.connect(self.database_url)
                cursor = conn.cursor()
                
                while current <= end:
                    # Verificar si el día actual está en los días seleccionados
                    # weekday() retorna 0=Lunes, 6=Domingo (igual que nuestro mapeo)
                    if current.weekday() in day_numbers:
                        # Crear slot de una hora comenzando en start_time
                        cursor.execute('''
                            INSERT INTO schedules (professional_id, date, start_time, available)
                            VALUES (%s, %s, %s, TRUE)
                        ''', (professional_id, current.strftime('%Y-%m-%d'), start_time))
                        schedules_created += 1
                    
                    # Ir al siguiente día
                    current += timedelta(days=1)
                
                # Hacer commit explícito
                conn.commit()
                cursor.close()
                
                return True, f"✅ {schedules_created} horarios creados exitosamente"
            
            finally:
                if conn:
                    conn.close()
        
        except Exception as e:
            return False, f"❌ Error: {str(e)}"