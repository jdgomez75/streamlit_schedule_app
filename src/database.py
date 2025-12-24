import psycopg2
import uuid
import requests
import os
import bcrypt
import json
from psycopg2 import sql
from datetime import datetime, time, date
from decimal import Decimal
from contextlib import contextmanager
from dotenv import load_dotenv
from psycopg2.errors import UniqueViolation

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
        """Convierte una fila de PostgreSQL a diccionario, convirtiendo tipos especiales (incluyendo Decimal)."""
        
        if row is None:
            return None # Importante si la función fue llamada después de fetchone()

        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
        
        # Convertir Decimales, tiempos y fechas
        for key, value in result.items():
            if isinstance(value, Decimal): # <--- CORRECCIÓN PRINCIPAL: Decimal a float
                result[key] = float(value)
            elif isinstance(value, time):
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
                return True, booking_code, booking_id
        
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
    
    # ==================== MÉTODOS DE PAGOS - VERSIÓN MEJORADA ====================
    # Agrega estas funciones a tu clase Database en database.py

    def create_payment(self, booking_code, booking_id, amount, payment_method='deposit', payment_status='pending'):
        """
        Crea un registro de pago en la base de datos
        
        Args:
            booking_code (str): Código de la cita
            booking_id (int): ID de la cita
            amount (float): Monto del pago
            payment_method (str): Método de pago ('deposit', 'full', 'partial')
            payment_status (str): Estado del pago ('pending', 'paid', 'verified')
        
        Returns:
            tuple: (success: bool, payment_id: int or error_message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments 
                    (booking_code, booking_id, amount, payment_method, payment_status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (booking_code, booking_id, float(amount), payment_method, payment_status, datetime.now()))
                
                payment_id = cursor.fetchone()[0]
                conn.commit()
                
                print(f"✅ Pago creado exitosamente - ID: {payment_id}")
                return True, payment_id
        
        except Exception as e:
            print(f"❌ Error en create_payment: {str(e)}")
            return False, f"❌ Error al crear pago: {str(e)}"


    def confirm_payment_with_operation(self, booking_code, payment_id, payment_data):
        """
        Confirma un pago después de validarlo con Mercado Pago
        
        Args:
            booking_code (str): Código de la cita
            payment_id (str): ID del pago en Mercado Pago (mercado_pago_id)
            payment_data (dict): Datos del pago validados
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Buscar si existe un pago para este booking_code
                cursor.execute('''
                    SELECT id, booking_id FROM payments 
                    WHERE booking_code = %s
                ''', (booking_code,))
                
                existing_payment = cursor.fetchone()
                
                if existing_payment:
                    # Actualizar el pago existente
                    payment_record_id = existing_payment[0]
                    
                    cursor.execute('''
                        UPDATE payments
                        SET 
                            mercado_pago_id = %s,
                            amount = %s,
                            payment_method = %s,
                            payment_status = %s,
                            verified = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (
                        str(payment_id),
                        payment_data.get('amount'),
                        payment_data.get('payment_method', 'credit_card'),
                        'verified',
                        payment_record_id
                    ))
                else:
                    # Crear un nuevo pago (si aún no existe)
                    # Primero obtener el booking_id del booking_code
                    cursor.execute('SELECT id FROM bookings WHERE booking_code = %s', (booking_code,))
                    booking_row = cursor.fetchone()
                    
                    if not booking_row:
                        return False, f"❌ No se encontró la cita {booking_code}"
                    
                    booking_id = booking_row[0]
                    
                    cursor.execute('''
                        INSERT INTO payments
                        (booking_code, booking_id, amount, payment_method, payment_status, 
                        mercado_pago_id, verified, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (
                        booking_code,
                        booking_id,
                        payment_data.get('amount'),
                        payment_data.get('payment_method', 'credit_card'),
                        'verified',
                        str(payment_id)
                    ))
                
                # 2. Actualizar el estado de la cita
                cursor.execute('''
                    UPDATE bookings
                    SET status = 'confirmed', 
                        deposit_paid = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                ''', (payment_data.get('amount'), booking_code))
                conn.commit()
                
                print(f"✅ Pago confirmado - Booking: {booking_code}, MP ID: {payment_id}")
                return True, f"✅ Pago confirmado exitosamente. ID Mercado Pago: {payment_id}"
        
        except Exception as e:
            print(f"❌ Error en confirm_payment_with_operation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"❌ Error al confirmar pago: {str(e)}"


    def update_payment_status(self, payment_id, payment_status):
        """
        Actualiza el estado de un pago
        
        Args:
            payment_id (int): ID del pago en la BD local
            payment_status (str): Nuevo estado ('pending', 'paid', 'verified', 'failed', 'cancelled')
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET payment_status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (payment_status, payment_id))
                
                conn.commit()
                return True, "✅ Estado del pago actualizado"
        
        except Exception as e:
            print(f"❌ Error en update_payment_status: {str(e)}")
            return False, f"❌ Error: {str(e)}"


    def get_payment_by_booking_code(self, booking_code):
        """
        Obtiene el pago más reciente de una cita
        
        Args:
            booking_code (str): Código de la cita
        
        Returns:
            dict: Datos del pago o None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments 
                    WHERE booking_code = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (booking_code,))
                
                row = cursor.fetchone()
                return self._row_to_dict(cursor, row) if row else None
        
        except Exception as e:
            print(f"❌ Error en get_payment_by_booking_code: {str(e)}")
            return None


    def get_payments_by_booking(self, booking_code):
        """
        Obtiene TODOS los pagos de una cita
        
        Args:
            booking_code (str): Código de la cita
        
        Returns:
            list: Lista de pagos ordenados por fecha (más recientes primero)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments 
                    WHERE booking_code = %s 
                    ORDER BY created_at DESC
                ''', (booking_code,))
                
                return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
        
        except Exception as e:
            print(f"❌ Error en get_payments_by_booking: {str(e)}")
            return []


    def update_deposit_paid(self, booking_code, deposit_amount):
        """
        Actualiza el anticipo pagado de una cita
        
        Args:
            booking_code (str): Código de la cita
            deposit_amount (float): Monto del anticipo
        
        Returns:
            tuple: (success: bool, message: str)
        """
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
            print(f"❌ Error en update_deposit_paid: {str(e)}")
            return False, f"❌ Error: {str(e)}"

    def upload_payment_receipt(self, booking_code, receipt_path):
        """
        Registra un comprobante de pago
        
        Args:
            booking_code (str): Código de la cita
            receipt_path (str): Ruta/URL del comprobante
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET receipt_image_path = %s, receipt_uploaded_at = CURRENT_TIMESTAMP
                    WHERE booking_code = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (receipt_path, booking_code))
                
                conn.commit()
                return True, "✅ Comprobante registrado"
        
        except Exception as e:
            print(f"❌ Error en upload_payment_receipt: {str(e)}")
            return False, f"❌ Error: {str(e)}"


    def verify_payment(self, payment_id):
        """
        Marca un pago como verificado
        
        Args:
            payment_id (int): ID del pago
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET verified = TRUE, 
                        payment_status = 'verified',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (payment_id,))
                
                conn.commit()
                return True, "✅ Pago verificado"
        
        except Exception as e:
            print(f"❌ Error en verify_payment: {str(e)}")
            return False, f"❌ Error: {str(e)}"


    def get_pending_payments(self):
        """
        Obtiene todos los pagos pendientes del sistema
        
        Returns:
            list: Lista de pagos pendientes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments 
                    WHERE payment_status = 'pending'
                    ORDER BY created_at DESC
                ''')
                
                return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
        
        except Exception as e:
            print(f"❌ Error en get_pending_payments: {str(e)}")
            return []


    def get_verified_payments(self, start_date=None, end_date=None):
        """
        Obtiene pagos verificados en un rango de fechas
        
        Args:
            start_date (str): Fecha inicio (YYYY-MM-DD) - opcional
            end_date (str): Fecha fin (YYYY-MM-DD) - opcional
        
        Returns:
            list: Lista de pagos verificados
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if start_date and end_date:
                    cursor.execute('''
                        SELECT * FROM payments 
                        WHERE payment_status = 'verified'
                        AND DATE(created_at) BETWEEN %s AND %s
                        ORDER BY created_at DESC
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT * FROM payments 
                        WHERE payment_status = 'verified'
                        ORDER BY created_at DESC
                    ''')
                
                return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]
        
        except Exception as e:
            print(f"❌ Error en get_verified_payments: {str(e)}")
            return []


    def get_payment_summary(self, start_date=None, end_date=None):
        """
        Obtiene un resumen de pagos para reportes
        
        Args:
            start_date (str): Fecha inicio (YYYY-MM-DD) - opcional
            end_date (str): Fecha fin (YYYY-MM-DD) - opcional
        
        Returns:
            dict: Resumen de pagos con totales
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if start_date and end_date:
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as total_payments,
                            SUM(amount) as total_amount,
                            AVG(amount) as average_amount,
                            COUNT(CASE WHEN payment_status = 'verified' THEN 1 END) as verified_count,
                            COUNT(CASE WHEN payment_status = 'pending' THEN 1 END) as pending_count,
                            COUNT(CASE WHEN verified = TRUE THEN 1 END) as verified_true_count
                        FROM payments
                        WHERE DATE(created_at) BETWEEN %s AND %s
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as total_payments,
                            SUM(amount) as total_amount,
                            AVG(amount) as average_amount,
                            COUNT(CASE WHEN payment_status = 'verified' THEN 1 END) as verified_count,
                            COUNT(CASE WHEN payment_status = 'pending' THEN 1 END) as pending_count,
                            COUNT(CASE WHEN verified = TRUE THEN 1 END) as verified_true_count
                        FROM payments
                    ''')
                
                row = cursor.fetchone()
                return self._row_to_dict(cursor, row) if row else {}
        
        except Exception as e:
            print(f"❌ Error en get_payment_summary: {str(e)}")
            return {}
    
    def get_required_deposit(self, booking_id):
        """Obtiene el depósito requerido (máximo de los servicios de la cita)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(s.deposit) as required_deposit
                FROM booking_services bs
                JOIN services s ON bs.service_id = s.id
                WHERE bs.booking_id = %s
            ''', (booking_id,))
            
            result = cursor.fetchone()
            return result[0] if result[0] else 0
        
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
        Genera bloques de UNA HORA por cada hora entre start_time y end_time
        
        Parámetros:
            professional_id (int): ID del profesional
            start_date (str): Fecha inicio 'YYYY-MM-DD'
            end_date (str): Fecha fin 'YYYY-MM-DD'
            start_time (str): Hora inicio 'HH:MM' (ej: '09:00')
            end_time (str): Hora fin 'HH:MM' (ej: '18:00')
            days_of_week (list): Lista de números de días [0=Lunes, 6=Domingo]
        
        Retorna:
            (bool, str): (éxito, mensaje)
        """
        try:
            from datetime import datetime, timedelta, time
            
            # Convertir strings a dates
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Convertir strings de hora a objetos time
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
            
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
                return False, f"❌ No se especificaron días válidos. Recibido: {days_of_week}"
            
            # Generar fechas y crear horarios
            current = start
            schedules_created = 0
            conn = None
            
            try:
                # Conectar directamente
                conn = psycopg2.connect(self.database_url)
                cursor = conn.cursor()
                
                while current <= end:
                    # Verificar si el día actual está en los días seleccionados
                    if current.weekday() in day_numbers:
                        # Crear slots cada hora desde start_time hasta end_time
                        current_time = start_time_obj
                        
                        while current_time < end_time_obj:
                            # Insertar slot para esta hora
                            cursor.execute('''
                                INSERT INTO schedules (professional_id, date, start_time, available)
                                VALUES (%s, %s, %s, TRUE)
                            ''', (professional_id, current.strftime('%Y-%m-%d'), current_time.strftime('%H:%M')))
                            
                            schedules_created += 1
                            
                            # Pasar a la siguiente hora
                            current_time = (datetime.combine(datetime.today(), current_time) + timedelta(hours=1)).time()
                    
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


# ==================== MÉTODOS DE AUTENTICACIÓN ====================
    def get_all_users_for_auth(self):
        """Obtiene todos los usuarios (username, hash, name) para la autenticación."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Selecciona solo los campos necesarios para la autenticación
                cursor.execute("SELECT username, password_hash, name FROM users")
                users = cursor.fetchall()
                
                # Formato esperado por streamlit-authenticator
                usernames = [u[0] for u in users]
                # ¡CRUCIAL! Asegurarse de que el hash sea un string
                passwords = [
                    u[1].decode('utf-8') if isinstance(u[1], bytes) else u[1] 
                    for u in users
                ]
                names = [u[2] for u in users]
                
                return usernames, passwords, names

    def get_all_users(self):
        """Obtiene todos los usuarios con ID para la gestión."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, username, name FROM users ORDER BY name")
                # Usa la función auxiliar _row_to_dict para un mejor manejo
                users = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
                return users

    def create_user(self, username, password, name):
        """Crea un nuevo usuario con hash de contraseña."""
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, name) VALUES (%s, %s, %s)",
                        (username, hashed_password, name)
                    )
                conn.commit()
            return True, "Usuario creado exitosamente"
        except UniqueViolation:
            return False, f"❌ Error: El usuario '{username}' ya existe."
        except Exception as e:
            return False, f"❌ Error al crear usuario: {e}"

    def delete_user(self, user_id):
        """Elimina un usuario por ID."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
            return True, "Usuario eliminado exitosamente"
        except Exception as e:
            return False, f"❌ Error al eliminar usuario: {e}"

    def update_password(self, username, new_password):
        """Actualiza la contraseña de un usuario."""
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET password_hash = %s WHERE username = %s",
                        (hashed_password, username)
                    )
                conn.commit()
            return True, "Contraseña actualizada exitosamente"
        except Exception as e:
            return False, f"❌ Error al actualizar contraseña: {e}"

    # ==================== USO EN admin.py ====================
    """
    Para usar estos métodos en tu admin.py, agrega esto después de autenticarte:

    # En lugar de consultar directamente
    user = get_user_from_db(db, username)
    if user and verify_password(password, user['password_hash']):
        # Puedes hacer esto:
        user = db.authenticate_user(username, password_hash)
        
    # Para registrar un usuario
    success, message = db.register_new_user(username, email, name, password_hash)

    # Para obtener un usuario
    user = db.get_user_by_username(username)

    # Para cambiar contraseña
    success, message = db.update_user_password(user_id, new_password_hash)

    # Para obtener todos los usuarios
    all_users = db.get_all_users()

    # Para eliminar un usuario
    success, message = db.delete_user(user_id)
    """

    def validate_mercadopago_payment(self, payment_id, booking_code, access_token):
        """
        Valida un pago en Mercado Pago usando el payment_id proporcionado por el usuario.
        
        Args:
            payment_id (str): ID del pago de Mercado Pago (proporcionado por el usuario)
            booking_code (str): Código de la cita para referencia cruzada
            access_token (str): Token de acceso de Mercado Pago
        
        Returns:
            tuple: (is_valid: bool, payment_data: dict, error_message: str)
        """
        try:
            # Validar que el payment_id no esté vacío
            if not payment_id or not str(payment_id).strip():
                return False, {}, "El ID de pago no puede estar vacío"
            
            # URL de la API de Mercado Pago para obtener detalles del pago
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Realizar petición a Mercado Pago
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            payment = response.json()
            
            # Validar que el pago exista
            if not payment or "id" not in payment:
                return False, {}, "El pago no fue encontrado en Mercado Pago"
            
            # Validar que el estado sea aprobado
            status = payment.get("status")
            if status != "approved":
                return False, {}, f"El pago no está aprobado. Estado actual: {status}"
            
            # Validar que la referencia externa coincida con el booking_code
            external_reference = payment.get("external_reference")
            if external_reference and external_reference != booking_code:
                return False, {}, f"El pago no corresponde a esta cita. Referencia esperada: {booking_code}"
            
            # Extraer datos del pago
            payment_data = {
                "operation_id": payment.get("id"),
                "amount": payment.get("transaction_amount"),
                "status": status,
                "date": payment.get("date_approved"),
                "payer_email": payment.get("payer", {}).get("email"),
                "payment_method": payment.get("payment_method", {}).get("type"),
                "payment_type": payment.get("payment_type_id"),  # credit_card, debit_card, account_money, etc.
                "currency": payment.get("currency_id")
            }
            
            return True, payment_data, None
        
        except requests.exceptions.Timeout:
            return False, {}, "Tiempo de espera agotado. Intenta nuevamente"
        
        except requests.exceptions.ConnectionError:
            return False, {}, "Error de conexión con Mercado Pago. Verifica tu conexión a internet"
        
        except requests.exceptions.HTTPError as e:
            # Manejar errores específicos de HTTP
            if e.response.status_code == 404:
                return False, {}, "El ID de pago no existe en Mercado Pago"
            elif e.response.status_code == 401:
                return False, {}, "Token de Mercado Pago inválido o expirado"
            else:
                error_detail = ""
                try:
                    error_detail = e.response.json().get("message", str(e))
                except:
                    error_detail = str(e)
                return False, {}, f"Error en la validación: {error_detail}"
        
        except Exception as e:
            return False, {}, f"Error inesperado: {str(e)}"
        
    # ============================================
    # FUNCIONES DE CATEGORÍAS
    # ============================================
    
    def get_active_categories(self):
        """
        Obtiene todas las categorías activas con su contador de servicios
        
        Returns:
            list: [{'id': int, 'name': str, 'icon': str, 'service_count': int}, ...]
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.id,
                    c.name,
                    c.icon,
                    c.description,
                    c.color,
                    COUNT(s.id) as service_count
                FROM categories c
                LEFT JOIN services s ON c.id = s.category_id AND s.active = TRUE
                WHERE c.active = TRUE
                GROUP BY c.id, c.name, c.icon, c.description, c.color
                HAVING COUNT(s.id) > 0
                ORDER BY c.name
            """)
            
            categories = []
            for row in cursor.fetchall():
                categories.append({
                    'id': row[0],
                    'name': row[1],
                    'icon': row[2],
                    'description': row[3],
                    'color': row[4],
                    'service_count': row[5]
                })
            
            return categories

    def get_category_by_id(self, category_id):
        """
        Obtiene una categoría por ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, icon, color, active
                FROM categories
                WHERE id = %s
            """, (category_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'icon': row[3],
                    'color': row[4],
                    'active': row[5]
                }
            return None

    def get_services_by_category(self, category_id):
        """Obtiene todos los servicios activos de una categoría"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM services WHERE category_id = %s AND active = TRUE ORDER BY name',
                (category_id,)
            )
            
            return [self._row_to_dict(cursor, row) for row in cursor.fetchall()]

    def create_category(self, name, description="", icon="📁", color="#EC4899"):
        """
        Crea una nueva categoría
        
        Returns:
            tuple: (success: bool, message: str, category_id: int or None)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO categories (name, description, icon, color, active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    RETURNING id
                """, (name.strip(), description, icon, color))
                
                category_id = cursor.fetchone()[0]
                conn.commit()
                
                return True, f"Categoría '{name}' creada exitosamente", category_id
        
        except Exception as e:
            if 'unique' in str(e).lower():
                return False, f"La categoría '{name}' ya existe", None
            return False, f"Error al crear categoría: {str(e)}", None

    def update_category(self, category_id, name=None, description=None, icon=None, color=None):
        """
        Actualiza una categoría
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                values = []
                
                if name:
                    updates.append("name = %s")
                    values.append(name.strip())
                if description is not None:
                    updates.append("description = %s")
                    values.append(description)
                if icon:
                    updates.append("icon = %s")
                    values.append(icon)
                if color:
                    updates.append("color = %s")
                    values.append(color)
                
                if not updates:
                    return False, "No hay cambios para actualizar"
                
                values.append(category_id)
                
                query = f"UPDATE categories SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(query, values)
                conn.commit()
                
                return True, "Categoría actualizada"
        
        except Exception as e:
            return False, f"Error al actualizar: {str(e)}"

    def toggle_category_active(self, category_id, active):
        """
        Activa/desactiva una categoría
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE categories SET active = %s WHERE id = %s
                """, (active, category_id))
                conn.commit()
                return True, "Categoría actualizada"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def get_duplicate_categories(self):
        """
        Encuentra categorías duplicadas o mal formateadas
        
        Returns:
            list: Categorías con variaciones en nombre
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    LOWER(TRIM(category)) as cat_clean,
                    COUNT(*) as count,
                    array_agg(DISTINCT category) as variantes,
                    COUNT(DISTINCT category) as num_variantes
                FROM services
                WHERE category IS NOT NULL
                GROUP BY LOWER(TRIM(category))
                HAVING COUNT(*) > 0
                ORDER BY count DESC
            """)
            
            duplicates = []
            for row in cursor.fetchall():
                if row[3] > 1:  # Si hay múltiples variaciones
                    duplicates.append({
                        'clean_name': row[0],
                        'total_services': row[1],
                        'variations': row[2],
                        'num_variations': row[3]
                    })
            
            return duplicates

    def normalize_service_categories(self, mapping_dict):
        """
        Normaliza categorías de servicios basado en un mapeo
        
        Args:
            mapping_dict: {'categoria_actual': 'categoria_nueva', ...}
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for old_cat, new_cat in mapping_dict.items():
                    cursor.execute("""
                        UPDATE services
                        SET category = %s
                        WHERE LOWER(TRIM(category)) = LOWER(TRIM(%s))
                    """, (new_cat, old_cat))
                
                conn.commit()
                return True, "Categorías normalizadas exitosamente"
        
        except Exception as e:
            return False, f"Error al normalizar: {str(e)}"
