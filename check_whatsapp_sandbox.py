#!/usr/bin/env python3
"""
Script para verificar el estado del sandbox de WhatsApp
"""
import os
from twilio.rest import Client

def check_whatsapp_sandbox():
    """Verifica el estado del sandbox de WhatsApp"""
    
    print("🔍 Verificando configuración de WhatsApp Sandbox...")
    
    # Obtener credenciales
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    
    if not account_sid or not auth_token:
        print("❌ Credenciales de Twilio no configuradas")
        return
    
    print(f"📱 Account SID: {account_sid}")
    print(f"📞 From Number: {from_number}")
    
    try:
        # Crear cliente de Twilio
        client = Client(account_sid, auth_token)
        
        # Obtener información de la cuenta
        account = client.api.accounts(account_sid).fetch()
        print(f"🏢 Account Name: {account.friendly_name}")
        print(f"💰 Account Type: {account.type}")
        
        # Verificar si es sandbox
        if "sandbox" in from_number.lower() or "14155238886" in from_number:
            print("🔧 Modo: Twilio WhatsApp Sandbox")
            print("⚠️  Limitaciones del Sandbox:")
            print("   - Solo números que hayan enviado 'join <sandbox-key>'")
            print("   - Máximo 1000 mensajes/mes")
            print("   - Solo para pruebas")
            print("\n📝 Para enviar mensajes:")
            print("   1. Ve a https://console.twilio.com/")
            print("   2. Busca 'WhatsApp Sandbox'")
            print("   3. Copia el sandbox key")
            print("   4. El destinatario debe enviar 'join <sandbox-key>' al número +14155238886")
        else:
            print("🚀 Modo: Twilio WhatsApp Business (Producción)")
            print("✅ Sin limitaciones de números")
            print("✅ Para uso en producción")
        
        # Verificar balance
        try:
            balance = client.api.balance.fetch()
            print(f"💳 Balance: ${balance.balance} {balance.currency}")
        except Exception as e:
            print(f"⚠️  No se pudo obtener balance: {e}")
            
    except Exception as e:
        print(f"❌ Error conectando con Twilio: {e}")

if __name__ == "__main__":
    check_whatsapp_sandbox()
