import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv


def enviar_confirmacion_cita(booking_data):
    """
    Envía correo de confirmación usando los datos de booking
    """
    
    # Extraer datos del booking
    cliente = booking_data['client']
    cita = booking_data['appointment']
    servicios = booking_data['services']
    profesional = booking_data['professional']
    pago = booking_data['payment']
    codigo = booking_data['booking_code']
    
    # Generar HTML de servicios
    servicios_html = ""
    for servicio in servicios:
        servicios_html += f"""
        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e0e0e0;">
            <span>{servicio['name']}</span>
            <span style="font-weight: 600; color: #667eea;">${servicio['price']:.2f}</span>
        </div>
        """
    
    # HTML del correo
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%); color: white; padding: 40px 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .content {{ padding: 30px; }}
            .box {{ background: #f0f7ff; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 4px; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; }}
            .label {{ font-weight: 600; color: #555; }}
            .value {{ color: #333; }}
            .services-section {{ margin: 20px 0; }}
            .total-section {{ padding: 20px 0; border-top: 2px solid #667eea; margin-top: 20px; }}
            .total-row {{ display: flex; justify-content: space-between; padding: 8px 0; font-size: 16px; }}
            .grand-total {{ font-weight: 700; font-size: 18px; color: #667eea; }}
            .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 13px; color: #666; border-top: 1px solid #e0e0e0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>✓ Cita Confirmada</h1>
                <p>Tu reserva ha sido registrada exitosamente</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                <p style="font-size: 18px;">Hola <strong>{cliente.get('name', 'Cliente')}</strong>,</p>
                
                <p>¡Excelente! Nos complace confirmar que tu cita ha sido reservada en <strong>Rubí Mata Salón</strong>.</p>
                
                <!-- Cita Details -->
                <div class="box">
                    <h3 style="margin-top: 0; color: #667eea;">📋 Detalles de tu Cita</h3>
                    
                    <div class="detail-row">
                        <span class="label">Código de Reserva:</span>
                        <span class="value"><strong>{codigo}</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">📅 Fecha:</span>
                        <span class="value">{cita['date']} ({cita['day']})</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">🕒 Hora:</span>
                        <span class="value">{cita['start_time']} - {cita['end_time']}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">⏱️ Duración:</span>
                        <span class="value">{cita['duration']}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">💇 Profesional:</span>
                        <span class="value">{profesional['name']}</span>
                    </div>
                </div>
                
                <!-- Servicios -->
                <div class="services-section">
                    <h4>🎨 Servicios Contratados:</h4>
                    <div style="background: #f9f9f9; padding: 15px; border-radius: 4px;">
                        {servicios_html}
                    </div>
                </div>
                
                <!-- Pago -->
                <div class="total-section">
                    <div class="total-row">
                        <span>Subtotal:</span>
                        <span>${pago['total']:.2f}</span>
                    </div>
                    <div class="total-row">
                        <span>Depósito a Pagar:</span>
                        <span style="color: #667eea; font-weight: 600;">${pago['deposit']:.2f}</span>
                    </div>
                    <div class="total-row">
                        <span>Pendiente en Cita:</span>
                        <span>${pago['remaining']:.2f}</span>
                    </div>
                    <div class="total-row grand-total">
                        <span>Total:</span>
                        <span>${pago['total']:.2f}</span>
                    </div>
                </div>
                
                <!-- Información Importante -->
                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <strong style="color: #856404;">⚠️ Información Importante:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px; color: #856404;">
                        <li>Por favor llega 10 minutos antes de tu cita</li>
                        <li>Si necesitas cancelar, hazlo con mínimo 24 horas de anticipación</li>
                        <li>Conserva tu código de reserva para futuras referencias</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    Si tienes alguna pregunta o necesitas hacer cambios, no dudes en contactarnos. 
                    <br>Estamos aquí para ayudarte. 💬
                </p>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p><strong>Rubí Mata Salón</strong></p>
                <p>Tu salón de belleza de confianza</p>
                <p>📞 +593 999 999 999 | 📧 info@rubimatasalon.com.mx</p>
                <p style="margin-top: 10px; font-size: 11px; color: #999;">
                    © 2025 Rubí Mata Salón. Todos los derechos reservados.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Configurar correo
    remitente = os.getenv("GMAIL_USER", "tu_email@gmail.com")
    contraseña = os.getenv("GMAIL_PASSWORD", "tu_contraseña_app")
    destinatario = cliente.get('email', '')
    
    if not destinatario:
        print("❌ Error: El cliente no tiene email registrado")
        return False
    
    # Crear mensaje
    msg = MIMEMultipart("alternative")
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = f"✓ Cita Confirmada - {codigo}"
    
    msg.attach(MIMEText(html_content, 'html'))
    
    # Enviar
    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, contraseña)
        servidor.send_message(msg)
        servidor.quit()
        
        print(f"✅ Correo enviado a {destinatario}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de autenticación en Gmail")
        return False
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        return False

def enviar_cancelacion_cita(booking_data, razon_cancelacion=""):
    """
    Envía correo de cancelación de cita
    """
    
    cliente = booking_data['client']
    cita = booking_data['appointment']
    codigo = booking_data['booking_code']
    pago = booking_data['payment']
    profesional = booking_data['professional']
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); color: white; padding: 40px 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .content {{ padding: 30px; }}
            .info-box {{ background: #FEE2E2; border-left: 4px solid #EF4444; padding: 20px; margin: 20px 0; border-radius: 4px; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e0e0e0; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ font-weight: 600; color: #555; }}
            .value {{ color: #333; }}
            .codigo {{ background: #f0f0f0; padding: 10px; border-radius: 4px; font-family: monospace; font-weight: bold; }}
            .refund-box {{ background: #DBEAFE; border-left: 4px solid #3B82F6; padding: 15px; margin: 20px 0; border-radius: 4px; }}
            .refund-box strong {{ color: #1E40AF; }}
            .reason-box {{ background: #F3F4F6; padding: 15px; margin: 20px 0; border-radius: 4px; }}
            .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 13px; color: #666; border-top: 1px solid #e0e0e0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>❌ Cita Cancelada</h1>
                <p>Tu reserva ha sido cancelada</p>
            </div>
            
            <div class="content">
                <p style="font-size: 18px;">Hola <strong>{cliente.get('name', 'Cliente')}</strong>,</p>
                
                <p>Confirmamos que tu cita ha sido <strong>cancelada exitosamente</strong>.</p>
                
                <div class="info-box">
                    <h3 style="margin-top: 0; color: #DC2626;">📋 Cita Cancelada</h3>
                    
                    <div class="detail-row">
                        <span class="label">Código:</span>
                        <span class="codigo">{codigo}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">📅 Fecha:</span>
                        <span class="value">{cita['date']} ({cita.get('day', '')})</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">🕒 Hora:</span>
                        <span class="value">{cita['start_time']} - {cita['end_time']}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">💇 Profesional:</span>
                        <span class="value">{profesional['name']}</span>
                    </div>
                </div>
                
                <div class="refund-box">
                    <strong>💰 Información de Reembolso</strong>
                    <p style="margin: 10px 0 0 0; color: #1E40AF;">
                        El depósito de <strong>${pago['deposit']:.2f}</strong> será reembolsado a tu cuenta en 5-7 días hábiles.
                    </p>
                </div>
                
                """ + (f"""
                <div class="reason-box">
                    <strong>📝 Razón de cancelación:</strong>
                    <p style="margin: 10px 0 0 0; color: #666;">{razon_cancelacion}</p>
                </div>
                """ if razon_cancelacion else "") + """
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    Si tienes alguna pregunta o necesitas más información, 
                    no dudes en contactarnos.
                    <br><br>
                    ¡Esperamos verte pronto en Rubí Mata Salón! 💬
                </p>
            </div>
            
            <div class="footer">
                <p><strong>Rubí Mata Salón</strong></p>
                <p>Tu salón de belleza de confianza</p>
                <p>📞 +593 999 999 999 | 📧 info@rubimatasalon.com.mx</p>
                <p style="margin-top: 10px; font-size: 11px; color: #999;">
                    © 2025 Rubí Mata Salón. Todos los derechos reservados.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    remitente = os.getenv("GMAIL_USER")
    contraseña = os.getenv("GMAIL_PASSWORD")
    destinatario = cliente.get('email', '')
    
    if not destinatario:
        print("❌ Error: El cliente no tiene email registrado")
        return False
    
    msg = MIMEMultipart("alternative")
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = f"❌ Cita Cancelada - {codigo}"
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, contraseña)
        servidor.send_message(msg)
        servidor.quit()
        
        #print(f"✅ Correo de cancelación enviado a {destinatario}")
        return True
        
    except Exception as e:
        #print(f"❌ Error al enviar correo: {e}")
        return False
    
def enviar_confirmacion_cambio(client_name, client_email, booking_code, new_date, new_time, reason):
    """
    Envía correo de confirmación usando los datos de cambio
    """
    
    # HTML del correo
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #EC4899 0%, #A855F7 100%); color: white; padding: 40px 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .content {{ padding: 30px; }}
            .box {{ background: #f0f7ff; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 4px; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; }}
            .label {{ font-weight: 600; color: #555; }}
            .value {{ color: #333; }}
            .services-section {{ margin: 20px 0; }}
            .total-section {{ padding: 20px 0; border-top: 2px solid #667eea; margin-top: 20px; }}
            .total-row {{ display: flex; justify-content: space-between; padding: 8px 0; font-size: 16px; }}
            .grand-total {{ font-weight: 700; font-size: 18px; color: #667eea; }}
            .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 13px; color: #666; border-top: 1px solid #e0e0e0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>✓ Actualizción Confirmada</h1>
                <p>Tu reserva ha sido actualizada exitosamente</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                <p style="font-size: 18px;">Hola <strong>{client_name}</strong>,</p>
                
                <p>¡Excelente! Nos complace confirmar que tu cita ha sido actualizada en <strong>Rubí Mata Salón</strong>.</p>
                
                <!-- Cita Details -->
                <div class="box">
                    <h3 style="margin-top: 0; color: #667eea;">📋 Detalles de tu Cita</h3>
                    
                    <div class="detail-row">
                        <span class="label">Código de Reserva:</span>
                        <span class="value"><strong>{booking_code}</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">📅 Nueva Fecha:</span>
                        <span class="value">{new_date}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">🕒 Nueva Hora:</span>
                        <span class="value">{new_time}</span>
                    </div>
                    
                    
                    <div class="detail-row">
                        <span class="label"> Motivo:</span>
                        <span class="value">{reason}</span>
                    </div>
                </div>
                
                <!-- Información Importante -->
                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <strong style="color: #856404;">⚠️ Información Importante:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px; color: #856404;">
                        <li>Por favor llega 10 minutos antes de tu cita</li>
                        <li>Si necesitas cancelar, hazlo con mínimo 24 horas de anticipación</li>
                        <li>Conserva tu código de reserva para futuras referencias</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    Si tienes alguna pregunta o necesitas hacer cambios, no dudes en contactarnos. 
                    <br>Estamos aquí para ayudarte. 💬
                </p>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p><strong>Rubí Mata Salón</strong></p>
                <p>Tu salón de belleza de confianza</p>
                <p>📞 +593 999 999 999 | 📧 info@rubimatasalon.com.mx</p>
                <p style="margin-top: 10px; font-size: 11px; color: #999;">
                    © 2025 Rubí Mata Salón. Todos los derechos reservados.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Configurar correo
    remitente = os.getenv("GMAIL_USER", "tu_email@gmail.com")
    contraseña = os.getenv("GMAIL_PASSWORD", "tu_contraseña_app")
    destinatario = client_email
    
    if not destinatario:
        print("❌ Error: El cliente no tiene email registrado")
        return False
    
    # Crear mensaje
    msg = MIMEMultipart("alternative")
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = f"✓ Cita Confirmada - {booking_code}"
    
    msg.attach(MIMEText(html_content, 'html'))
    
    # Enviar
    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, contraseña)
        servidor.send_message(msg)
        servidor.quit()
        
        print(f"✅ Correo enviado a {destinatario}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Error de autenticación en Gmail")
        return False
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        return False
