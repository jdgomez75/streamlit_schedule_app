import sqlite3
import os

# ----------------------------------------------------------------------
# ⚠️ CAMBIA ESTO: Nombre de tu archivo de base de datos SQLite
# ----------------------------------------------------------------------
SQLITE_DB_FILE = 'beauty_clinic.db' 
# ----------------------------------------------------------------------

def export_create_tables(db_file):
    """
    Se conecta a la base de datos SQLite y exporta las sentencias CREATE TABLE.
    """
    if not os.path.exists(db_file):
        print(f"❌ Error: No se encontró el archivo de base de datos: {db_file}")
        return

    conn = None
    try:
        # Conexión a SQLite
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Consulta a la tabla maestra
        # type = 'table' filtra solo las tablas (excluyendo índices, vistas, etc.)
        # name NOT LIKE 'sqlite_%' excluye las tablas internas del sistema
        cursor.execute("""
            SELECT sql 
            FROM sqlite_master 
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
        """)
        
        results = cursor.fetchall()

        if not results:
            print("⚠️ Advertencia: No se encontraron tablas de usuario en la base de datos.")
            return

        print(f"--- Sentencias CREATE TABLE para {db_file} ---")
        
        # Imprimir cada sentencia SQL
        for row in results:
            # row[0] contiene la sentencia CREATE TABLE
            print(f"\n{row[0]};") 
        
        print("\n--- FIN DE EXPORTACIÓN ---")

    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {e}")
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_create_tables(SQLITE_DB_FILE)