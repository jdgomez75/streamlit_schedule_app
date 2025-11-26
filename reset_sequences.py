import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL no configurada")
    exit(1)

print("\n🔧 Reseteando secuencias de IDs en PostgreSQL...\n")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Obtener el máximo ID de cada tabla
    tables = [
        'services',
        'professionals',
        'professional_services',
        'schedules',
        'bookings',
        'booking_services',
        'payments',
        'booking_changes'
    ]
    
    for table in tables:
        try:
            # Obtener el máximo ID
            cursor.execute(f"SELECT MAX(id) FROM {table}")
            max_id = cursor.fetchone()[0]
            
            if max_id is not None:
                # Obtener el nombre de la secuencia
                cursor.execute(f"""
                    SELECT pg_get_serial_sequence('{table}', 'id')
                """)
                sequence = cursor.fetchone()[0]
                
                if sequence:
                    # Resetear la secuencia al siguiente valor
                    new_value = max_id + 1
                    cursor.execute(f"ALTER SEQUENCE {sequence} RESTART WITH {new_value}")
                    print(f"✅ {table:30} - ID máximo: {max_id:5} → Próximo: {new_value}")
                else:
                    print(f"⚠️  {table:30} - No tiene secuencia de ID")
            else:
                print(f"ℹ️  {table:30} - Tabla vacía")
        
        except psycopg2.Error as e:
            print(f"⚠️  {table:30} - Error: {str(e)[:50]}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✅ ¡Secuencias reseteadas correctamente!\n")
    print("Ahora puedes crear citas sin problemas de ID duplicados.")
    
except psycopg2.Error as e:
    print(f"\n❌ Error: {str(e)}\n")
    exit(1)
