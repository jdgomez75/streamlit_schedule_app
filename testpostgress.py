import sqlite3
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv
import sys

# Cargar variables de entorno
load_dotenv()

# Configuración
SQLITE_DB = 'beauty_clinic.db'
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL no está configurada")
    print("Configura tu .env file con: DATABASE_URL=postgresql://...")
    sys.exit(1)

class MigrationManager:
    """Gestor de migración con conversión de tipos y manejo de FK"""
    
    def __init__(self, sqlite_path, postgres_url):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.stats = {
            'services': 0,
            'professionals': 0,
            'professional_services': 0,
            'schedules': 0,
            'bookings': 0,
            'booking_services': 0,
            'payments': 0,
            'booking_changes': 0,
            'errors': []
        }
    
    def check_sqlite_db(self):
        """Verifica que la BD SQLite existe"""
        if not os.path.exists(self.sqlite_path):
            print(f"❌ Error: No se encuentra la BD SQLite: {self.sqlite_path}")
            return False
        
        print(f"✅ BD SQLite encontrada: {self.sqlite_path}\n")
        return True
    
    def get_sqlite_connection(self):
        """Crea conexión a SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌ Error conectando a SQLite: {e}")
            return None
    
    def get_postgres_connection(self):
        """Crea conexión a PostgreSQL"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            return conn
        except psycopg2.Error as e:
            print(f"❌ Error conectando a PostgreSQL: {e}")
            return None
    
    def disable_foreign_keys(self, cursor):
        """Desactiva las restricciones de Foreign Keys"""
        try:
            cursor.execute("ALTER TABLE booking_services DISABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE professional_services DISABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE schedules DISABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE bookings DISABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE payments DISABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE booking_changes DISABLE TRIGGER ALL;")
            print("⚙️  Foreign Keys desactivadas temporalmente\n")
        except Exception as e:
            print(f"⚠️  No se pudieron desactivar FK: {e}")
    
    def enable_foreign_keys(self, cursor):
        """Reactiva las restricciones de Foreign Keys"""
        try:
            cursor.execute("ALTER TABLE booking_services ENABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE professional_services ENABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE schedules ENABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE bookings ENABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE payments ENABLE TRIGGER ALL;")
            cursor.execute("ALTER TABLE booking_changes ENABLE TRIGGER ALL;")
            print("✅ Foreign Keys reactivadas\n")
        except Exception as e:
            print(f"⚠️  No se pudieron reactivar FK: {e}")
    
    def migrate_services(self):
        """Migra servicios de SQLite a PostgreSQL"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            # Obtener datos de SQLite
            sqlite_cursor.execute("SELECT id, name, description, price, duration, deposit, category, active FROM services")
            services = sqlite_cursor.fetchall()
            
            if not services:
                print("ℹ️  No hay servicios para migrar")
                return True
            
            print(f"📦 Migrando {len(services)} servicios...")
            
            # Insertar en PostgreSQL CON CASTING DE BOOLEAN
            for service in services:
                postgres_cursor.execute("""
                    INSERT INTO services (id, name, description, price, duration, deposit, category, active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::boolean)
                    ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    price = EXCLUDED.price,
                    duration = EXCLUDED.duration,
                    deposit = EXCLUDED.deposit,
                    category = EXCLUDED.category,
                    active = EXCLUDED.active
                """, (
                    service['id'],
                    service['name'],
                    service['description'],
                    service['price'],
                    service['duration'],
                    service['deposit'],
                    service['category'],
                    bool(service['active'])  # Convertir a boolean de Python
                ))
            
            postgres_conn.commit()
            self.stats['services'] = len(services)
            print(f"   ✅ {len(services)} servicios migrados\n")
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando servicios: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_professionals(self):
        """Migra profesionales de SQLite a PostgreSQL"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("SELECT id, name, email, phone, specialization, active FROM professionals")
            professionals = sqlite_cursor.fetchall()
            
            if not professionals:
                print("ℹ️  No hay profesionales para migrar")
                return True
            
            print(f"👥 Migrando {len(professionals)} profesionales...")
            
            for prof in professionals:
                postgres_cursor.execute("""
                    INSERT INTO professionals (id, name, email, phone, specialization, active)
                    VALUES (%s, %s, %s, %s, %s, %s::boolean)
                    ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    specialization = EXCLUDED.specialization,
                    active = EXCLUDED.active
                """, (
                    prof['id'],
                    prof['name'],
                    prof['email'],
                    prof['phone'],
                    prof['specialization'],
                    bool(prof['active'])  # Convertir a boolean de Python
                ))
            
            postgres_conn.commit()
            self.stats['professionals'] = len(professionals)
            print(f"   ✅ {len(professionals)} profesionales migrados\n")
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando profesionales: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_professional_services(self):
        """Migra relación profesionales-servicios"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("SELECT id, professional_id, service_id FROM professional_services")
            prof_services = sqlite_cursor.fetchall()
            
            if not prof_services:
                print("ℹ️  No hay asignaciones profesional-servicio para migrar")
                return True
            
            print(f"🔗 Migrando {len(prof_services)} asignaciones profesional-servicio...")
            
            skipped = 0
            for ps in prof_services:
                try:
                    postgres_cursor.execute("""
                        INSERT INTO professional_services (id, professional_id, service_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (ps['id'], ps['professional_id'], ps['service_id']))
                except psycopg2.IntegrityError as ie:
                    # Ignorar FK violations
                    skipped += 1
                    postgres_conn.rollback()
                    continue
            
            postgres_conn.commit()
            self.stats['professional_services'] = len(prof_services) - skipped
            print(f"   ✅ {len(prof_services) - skipped} asignaciones migradas")
            if skipped > 0:
                print(f"   ⚠️  {skipped} asignaciones descartadas (profesional no existe)\n")
            else:
                print()
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando asignaciones: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_schedules(self):
        """Migra horarios"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("SELECT id, professional_id, date, start_time, available FROM schedules")
            schedules = sqlite_cursor.fetchall()
            
            if not schedules:
                print("ℹ️  No hay horarios para migrar")
                return True
            
            print(f"⏰ Migrando {len(schedules)} horarios...")
            
            for sched in schedules:
                postgres_cursor.execute("""
                    INSERT INTO schedules (id, professional_id, date, start_time, available)
                    VALUES (%s, %s, %s, %s, %s::boolean)
                    ON CONFLICT (id) DO UPDATE SET
                    professional_id = EXCLUDED.professional_id,
                    date = EXCLUDED.date,
                    start_time = EXCLUDED.start_time,
                    available = EXCLUDED.available
                """, (
                    sched['id'],
                    sched['professional_id'],
                    sched['date'],
                    sched['start_time'],
                    bool(sched['available'])  # Convertir a boolean de Python
                ))
            
            postgres_conn.commit()
            self.stats['schedules'] = len(schedules)
            print(f"   ✅ {len(schedules)} horarios migrados\n")
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando horarios: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_bookings(self):
        """Migra citas"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("""
                SELECT id, booking_code, client_name, client_phone, client_email, 
                       date, start_time, end_time, professional_id, total_price, 
                       deposit_paid, status, created_at, updated_at
                FROM bookings
            """)
            bookings = sqlite_cursor.fetchall()
            
            if not bookings:
                print("ℹ️  No hay citas para migrar")
                return True
            
            print(f"📅 Migrando {len(bookings)} citas...")
            
            skipped = 0
            for booking in bookings:
                try:
                    postgres_cursor.execute("""
                        INSERT INTO bookings (id, booking_code, client_name, client_phone, client_email,
                                             date, start_time, end_time, professional_id, total_price,
                                             deposit_paid, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                        booking_code = EXCLUDED.booking_code,
                        client_name = EXCLUDED.client_name,
                        client_phone = EXCLUDED.client_phone,
                        client_email = EXCLUDED.client_email,
                        date = EXCLUDED.date,
                        start_time = EXCLUDED.start_time,
                        end_time = EXCLUDED.end_time,
                        professional_id = EXCLUDED.professional_id,
                        total_price = EXCLUDED.total_price,
                        deposit_paid = EXCLUDED.deposit_paid,
                        status = EXCLUDED.status,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at
                    """, (
                        booking['id'],
                        booking['booking_code'],
                        booking['client_name'],
                        booking['client_phone'],
                        booking['client_email'],
                        booking['date'],
                        booking['start_time'],
                        booking['end_time'],
                        booking['professional_id'],
                        booking['total_price'],
                        booking['deposit_paid'],
                        booking['status'],
                        booking['created_at'],
                        booking['updated_at']
                    ))
                except psycopg2.IntegrityError:
                    skipped += 1
                    postgres_conn.rollback()
                    continue
            
            postgres_conn.commit()
            self.stats['bookings'] = len(bookings) - skipped
            print(f"   ✅ {len(bookings) - skipped} citas migradas")
            if skipped > 0:
                print(f"   ⚠️  {skipped} citas descartadas (profesional no existe)\n")
            else:
                print()
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando citas: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_booking_services(self):
        """Migra servicios en citas"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("""
                SELECT id, booking_id, service_id, service_name, service_price
                FROM booking_services
            """)
            booking_services = sqlite_cursor.fetchall()
            
            if not booking_services:
                print("ℹ️  No hay servicios en citas para migrar")
                return True
            
            print(f"🛍️  Migrando {len(booking_services)} servicios en citas...")
            
            skipped = 0
            for bs in booking_services:
                try:
                    postgres_cursor.execute("""
                        INSERT INTO booking_services (id, booking_id, service_id, service_name, service_price)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                        booking_id = EXCLUDED.booking_id,
                        service_id = EXCLUDED.service_id,
                        service_name = EXCLUDED.service_name,
                        service_price = EXCLUDED.service_price
                    """, (
                        bs['id'],
                        bs['booking_id'],
                        bs['service_id'],
                        bs['service_name'],
                        bs['service_price']
                    ))
                except psycopg2.IntegrityError:
                    skipped += 1
                    postgres_conn.rollback()
                    continue
            
            postgres_conn.commit()
            self.stats['booking_services'] = len(booking_services) - skipped
            print(f"   ✅ {len(booking_services) - skipped} servicios migrados")
            if skipped > 0:
                print(f"   ⚠️  {skipped} servicios descartados (cita no existe)\n")
            else:
                print()
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando servicios en citas: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_payments(self):
        """Migra pagos"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("""
                SELECT id, booking_code, booking_id, amount, payment_method, payment_status,
                       mercado_pago_id, receipt_image_path, receipt_uploaded_at, verified,
                       created_at, updated_at
                FROM payments
            """)
            payments = sqlite_cursor.fetchall()
            
            if not payments:
                print("ℹ️  No hay pagos para migrar")
                return True
            
            print(f"💳 Migrando {len(payments)} pagos...")
            
            skipped = 0
            for payment in payments:
                try:
                    postgres_cursor.execute("""
                        INSERT INTO payments (id, booking_code, booking_id, amount, payment_method,
                                             payment_status, mercado_pago_id, receipt_image_path,
                                             receipt_uploaded_at, verified, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::boolean, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                        booking_code = EXCLUDED.booking_code,
                        booking_id = EXCLUDED.booking_id,
                        amount = EXCLUDED.amount,
                        payment_method = EXCLUDED.payment_method,
                        payment_status = EXCLUDED.payment_status,
                        mercado_pago_id = EXCLUDED.mercado_pago_id,
                        receipt_image_path = EXCLUDED.receipt_image_path,
                        receipt_uploaded_at = EXCLUDED.receipt_uploaded_at,
                        verified = EXCLUDED.verified,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at
                    """, (
                        payment['id'],
                        payment['booking_code'],
                        payment['booking_id'],
                        payment['amount'],
                        payment['payment_method'],
                        payment['payment_status'],
                        payment['mercado_pago_id'],
                        payment['receipt_image_path'],
                        payment['receipt_uploaded_at'],
                        bool(payment['verified']),  # Convertir a boolean de Python
                        payment['created_at'],
                        payment['updated_at']
                    ))
                except psycopg2.IntegrityError:
                    skipped += 1
                    postgres_conn.rollback()
                    continue
            
            postgres_conn.commit()
            self.stats['payments'] = len(payments) - skipped
            print(f"   ✅ {len(payments) - skipped} pagos migrados")
            if skipped > 0:
                print(f"   ⚠️  {skipped} pagos descartados (cita no existe)\n")
            else:
                print()
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando pagos: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def migrate_booking_changes(self):
        """Migra cambios en citas"""
        try:
            sqlite_conn = self.get_sqlite_connection()
            postgres_conn = self.get_postgres_connection()
            
            if not sqlite_conn or not postgres_conn:
                return False
            
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            sqlite_cursor.execute("""
                SELECT id, booking_code, booking_id, change_type, original_date, original_time,
                       new_date, new_time, reason, status, created_at
                FROM booking_changes
            """)
            changes = sqlite_cursor.fetchall()
            
            if not changes:
                print("ℹ️  No hay cambios de citas para migrar")
                return True
            
            print(f"📝 Migrando {len(changes)} cambios de citas...")
            
            skipped = 0
            for change in changes:
                try:
                    postgres_cursor.execute("""
                        INSERT INTO booking_changes (id, booking_code, booking_id, change_type,
                                                   original_date, original_time, new_date, new_time,
                                                   reason, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                        booking_code = EXCLUDED.booking_code,
                        booking_id = EXCLUDED.booking_id,
                        change_type = EXCLUDED.change_type,
                        original_date = EXCLUDED.original_date,
                        original_time = EXCLUDED.original_time,
                        new_date = EXCLUDED.new_date,
                        new_time = EXCLUDED.new_time,
                        reason = EXCLUDED.reason,
                        status = EXCLUDED.status,
                        created_at = EXCLUDED.created_at
                    """, (
                        change['id'],
                        change['booking_code'],
                        change['booking_id'],
                        change['change_type'],
                        change['original_date'],
                        change['original_time'],
                        change['new_date'],
                        change['new_time'],
                        change['reason'],
                        change['status'],
                        change['created_at']
                    ))
                except psycopg2.IntegrityError:
                    skipped += 1
                    postgres_conn.rollback()
                    continue
            
            postgres_conn.commit()
            self.stats['booking_changes'] = len(changes) - skipped
            print(f"   ✅ {len(changes) - skipped} cambios migrados")
            if skipped > 0:
                print(f"   ⚠️  {skipped} cambios descartados (cita no existe)\n")
            else:
                print()
            
            sqlite_cursor.close()
            sqlite_conn.close()
            postgres_cursor.close()
            postgres_conn.close()
            
            return True
        
        except Exception as e:
            error_msg = f"Error migrando cambios: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"❌ {error_msg}\n")
            return False
    
    def print_summary(self):
        """Imprime un resumen de la migración"""
        print("\n" + "="*70)
        print("📊 RESUMEN DE MIGRACIÓN")
        print("="*70)
        print(f"\n✅ Datos migrados exitosamente:")
        print(f"   📦 Servicios: {self.stats['services']}")
        print(f"   👥 Profesionales: {self.stats['professionals']}")
        print(f"   🔗 Asignaciones Prof-Svc: {self.stats['professional_services']}")
        print(f"   ⏰ Horarios: {self.stats['schedules']}")
        print(f"   📅 Citas: {self.stats['bookings']}")
        print(f"   🛍️  Servicios en Citas: {self.stats['booking_services']}")
        print(f"   💳 Pagos: {self.stats['payments']}")
        print(f"   📝 Cambios de Citas: {self.stats['booking_changes']}")
        
        total_records = sum([v for k, v in self.stats.items() if k != 'errors'])
        print(f"\n   📈 TOTAL DE REGISTROS: {total_records}")
        
        if self.stats['errors']:
            print(f"\n⚠️  ERRORES ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                print(f"   ❌ {error}")
        else:
            print(f"\n✨ ¡Migración completada sin errores!")
        
        print("\n" + "="*70 + "\n")
    
    def run_migration(self):
        """Ejecuta la migración completa"""
        print("\n" + "="*70)
        print("🚀 INICIANDO MIGRACIÓN DE SQLite A PostgreSQL")
        print("="*70 + "\n")
        
        if not self.check_sqlite_db():
            return False
        
        print("Migrando datos en orden (respetando relaciones)...\n")
        print("-" * 70 + "\n")
        
        # Orden importante para respetar FK
        steps = [
            ("Servicios", self.migrate_services),
            ("Profesionales", self.migrate_professionals),
            ("Asignaciones", self.migrate_professional_services),
            ("Horarios", self.migrate_schedules),
            ("Citas", self.migrate_bookings),
            ("Servicios en Citas", self.migrate_booking_services),
            ("Pagos", self.migrate_payments),
            ("Cambios en Citas", self.migrate_booking_changes),
        ]
        
        for step_name, migration_func in steps:
            migration_func()
        
        self.print_summary()
        return True

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("🔄 MIGRADOR DE BASE DE DATOS")
    print("SQLite → PostgreSQL")
    print("="*70)
    
    # Verificar que SQLite existe
    if not os.path.exists(SQLITE_DB):
        print(f"\n❌ Error: No se encuentra: {SQLITE_DB}")
        print("Asegúrate de que el archivo está en la carpeta actual")
        sys.exit(1)
    
    # Confirmar antes de migrar
    print(f"\n📁 BD SQLite: {SQLITE_DB}")
    print(f"🐘 BD PostgreSQL: Configurada en .env")
    
    confirmation = input("\n¿Deseas continuar con la migración? (si/no): ").strip().lower()
    
    if confirmation != 'si':
        print("❌ Migración cancelada")
        sys.exit(0)
    
    # Ejecutar migración
    migrator = MigrationManager(SQLITE_DB, DATABASE_URL)
    success = migrator.run_migration()
    
    if success:
        print("✨ ¡Migración completada!")
        print("\n💡 Próximos pasos:")
        print("   1. Verifica los datos en PostgreSQL")
        print("   2. Actualiza tu código para usar PostgreSQL")
        print("   3. Prueba la aplicación")
    else:
        print("❌ La migración falló. Revisa los errores arriba.")
        sys.exit(1)

if __name__ == "__main__":
    main()