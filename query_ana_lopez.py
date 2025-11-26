#!/usr/bin/env python3
"""
Script para consultar los horarios de Ana López en PostgreSQL
Bella Clinic
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL no configurada en .env")
    exit(1)

try:
    # Conectar a PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("🔍 Consultando horarios de Ana López...\n")
    
    # Query para obtener horarios de Ana López
    query = """
        SELECT *
        FROM schedules 
        WHERE date > '2026-01-01'
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if rows:
        # Obtener nombres de columnas
        columns = [desc[0] for desc in cursor.description]
        
        # Crear DataFrame
        df = pd.DataFrame(rows, columns=columns)
        
        # Mostrar información del profesional
        prof_name = rows[0][1]
        prof_id = rows[0][0]
        
        print(f"👤 Profesional: {prof_name}")
        print(f"🆔 ID: {prof_id}")
        print(f"📊 Total de horarios: {len(rows)}\n")
        
        # Mostrar tabla formateada
        print("=" * 100)
        print(f"{'Fecha':<12} {'Hora':<8} {'Estado':<15} {'Disponible':<12}")
        print("=" * 100)
        
        for row in rows:
            fecha = row[3]  # date
            hora = row[4]   # start_time
            estado = row[6] # estado
            disponible = "Sí" if row[5] else "No"  # available
            
            print(f"{str(fecha):<12} {str(hora):<8} {estado:<15} {disponible:<12}")
        
        print("=" * 100)
        
        # Estadísticas
        disponibles = sum(1 for row in rows if row[5] == True)
        ocupados = sum(1 for row in rows if row[5] == False)
        
        print(f"\n📈 Estadísticas:")
        print(f"   ✅ Horarios disponibles: {disponibles}")
        print(f"   ❌ Horarios ocupados: {ocupados}")
        print(f"   📅 Total: {len(rows)}")
        
        # Agrupar por fecha
        print(f"\n📅 Horarios por fecha:")
        fechas_unicas = {}
        for row in rows:
            fecha = str(row[3])
            if fecha not in fechas_unicas:
                fechas_unicas[fecha] = []
            fechas_unicas[fecha].append({
                'hora': str(row[4]),
                'disponible': row[5]
            })
        
        for fecha in sorted(fechas_unicas.keys()):
            horarios = fechas_unicas[fecha]
            print(f"   📌 {fecha}:")
            for h in horarios:
                icon = "✅" if h['disponible'] else "❌"
                print(f"      {icon} {h['hora']}")
    
    else:
        print("⚠️  No se encontraron horarios para Ana López")
        
        # Mostrar profesionales disponibles
        print("\n📋 Profesionales disponibles:")
        cursor.execute("SELECT id, name FROM professionals WHERE active = TRUE ORDER BY name")
        profs = cursor.fetchall()
        
        if profs:
            for prof in profs:
                print(f"   • {prof[1]} (ID: {prof[0]})")
        else:
            print("   No hay profesionales registrados")
    
    cursor.close()
    conn.close()
    
except psycopg2.Error as e:
    print(f"❌ Error de conexión a PostgreSQL: {str(e)}")
    exit(1)
except Exception as e:
    print(f"❌ Error: {str(e)}")
    exit(1)

print("\n✅ Consulta completada")
