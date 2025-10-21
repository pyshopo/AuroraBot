"""
Motor principal de Aura - Manejo de voz y procesamiento de comandos
"""
import speech_recognition as sr
from gtts import gTTS
import os
import platform
import time
import logging
from pathlib import Path

from config.settings import (
    VOICE_LANG, TTS_LANG, TEMP_AUDIO_FILE,
    ENERGY_THRESHOLD, DYNAMIC_ENERGY, LISTEN_TIMEOUT,
    PHRASE_TIME_LIMIT, AMBIENT_NOISE_DURATION,
    EXIT_COMMANDS, get_audio_player
)

from src.cerebro_ia import generar_respuesta
from src.habilidades_sistema import abrir_programa
from src.habilidades_web import abrir_pagina_web, buscar_en_google

# Configurar logging
logger = logging.getLogger(__name__)


def hablar(texto):
    """
    Convierte texto a voz usando gTTS y lo reproduce
    
    Args:
        texto (str): Texto a convertir en voz
    """
    try:
        # Generar audio con gTTS
        tts = gTTS(text=texto, lang=TTS_LANG)
        tts.save(TEMP_AUDIO_FILE)
        
        # Detectar sistema operativo
        sistema = platform.system()
        
        # Reproducir según el OS
        if sistema == "Windows":
            os.system(f'start {TEMP_AUDIO_FILE}')
        elif sistema == "Darwin":  # macOS
            os.system(f'afplay {TEMP_AUDIO_FILE}')
        else:  # Linux
            player_commands = get_audio_player()
            reproducido = False
            
            for player_cmd in player_commands:
                player_name = player_cmd.split()[0]
                if os.system(f'which {player_name} > /dev/null 2>&1') == 0:
                    os.system(f'{player_cmd} {TEMP_AUDIO_FILE}')
                    reproducido = True
                    break
            
            if not reproducido:
                logger.error("No se encontró un reproductor de audio")
                print("❌ No se encontró un reproductor de audio.")
                print("   Instala: mpg123, ffmpeg o vlc")
        
        # Esperar a que termine el audio
        time.sleep(len(texto) * 0.05)
        
    except Exception as e:
        logger.error(f"Error en función hablar: {e}")
        print(f"❌ Error en la función hablar: {e}")
    finally:
        # Limpiar archivo temporal
        try:
            if os.path.exists(TEMP_AUDIO_FILE):
                os.remove(TEMP_AUDIO_FILE)
        except Exception as e:
            logger.warning(f"No se pudo eliminar archivo temporal: {e}")


def escuchar():
    """
    Captura audio del micrófono y lo convierte a texto
    
    Returns:
        str: Comando en minúsculas
        None: Si no se detectó voz o hubo timeout
        "ERROR_MIC": Si hay problemas con el micrófono
    """
    r = sr.Recognizer()
    
    # Configurar sensibilidad
    r.energy_threshold = ENERGY_THRESHOLD
    r.dynamic_energy_threshold = DYNAMIC_ENERGY
    
    try:
        with sr.Microphone() as source:
            logger.debug("Ajustando para ruido ambiente...")
            print("🎤 Ajustando para ruido ambiente...")
            r.adjust_for_ambient_noise(source, duration=AMBIENT_NOISE_DURATION)
            
            logger.debug("Escuchando...")
            print("👂 Escuchando...")
            audio = r.listen(
                source, 
                timeout=LISTEN_TIMEOUT, 
                phrase_time_limit=PHRASE_TIME_LIMIT
            )
            
            logger.debug("Reconociendo...")
            print("🔄 Reconociendo...")
            comando = r.recognize_google(audio, language=VOICE_LANG)
            logger.info(f"Usuario dijo: {comando}")
            print(f"✅ Usuario dijo: {comando}")
            return comando.lower()
            
    except sr.WaitTimeoutError:
        logger.debug("Timeout - No se detectó voz")
        print("⏱️  Tiempo de espera agotado, no se detectó voz")
        return None
    except sr.UnknownValueError:
        logger.debug("No se pudo entender el audio")
        print("❓ No se pudo entender el audio")
        return None
    except sr.RequestError as e:
        logger.error(f"Error con el servicio de reconocimiento: {e}")
        print(f"🌐 Error con el servicio de reconocimiento: {e}")
        print("   Verifica tu conexión a internet")
        return "ERROR_MIC"
    except OSError as e:
        logger.error(f"Error crítico al acceder al micrófono: {e}")
        print(f"🎙️  Error crítico al acceder al micrófono: {e}")
        print("   Verifica que el micrófono esté conectado y configurado")
        return "ERROR_MIC"
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        print(f"❌ Error inesperado: {e}")
        return "ERROR_MIC"


def procesar_comando(comando):
    """
    Procesa el comando del usuario y ejecuta la acción correspondiente
    
    Args:
        comando (str): Comando a procesar
        
    Returns:
        tuple: (respuesta: str, seguir_escuchando: bool)
    """
    # Validar entrada
    if not comando or comando == "ERROR_MIC":
        return "", True
    
    # Verificar comandos de salida
    if any(palabra in comando for palabra in EXIT_COMMANDS):
        logger.info("Comando de salida detectado")
        return "¡Hasta luego! Fue un placer ayudarte.", False
    
    # Intentar ejecutar habilidades específicas
    habilidades = [
        ("Sistema", abrir_programa),
        ("Web", abrir_pagina_web),
        ("Búsqueda", buscar_en_google)
    ]
    
    for nombre, funcion in habilidades:
        try:
            respuesta = funcion(comando)
            if respuesta:
                logger.info(f"Habilidad '{nombre}' ejecutada")
                print(f"✅ Habilidad '{nombre}' ejecutada")
                return respuesta, True
        except Exception as e:
            logger.error(f"Error en habilidad '{nombre}': {e}")
            continue
    
    # Si ninguna habilidad específica respondió, usar la IA
    logger.info("Consultando a la IA...")
    print("🧠 Consultando a la IA...")
    try:
        respuesta_ia = generar_respuesta(comando)
        return respuesta_ia, True
    except Exception as e:
        logger.error(f"Error en generar_respuesta: {e}")
        return "Lo siento, tuve un problema procesando tu solicitud.", True


def modo_terminal():
    """
    Ejecuta Aura en modo terminal (sin interfaz gráfica)
    """
    print("=" * 60)
    print("🎯 AURA - Asistente de IA")
    print("=" * 60)
    print("Modo: Terminal")
    print("Comandos: Habla al micrófono o escribe 'salir'")
    print("=" * 60)
    print()
    
    hablar("Hola, soy Aura. Sistema iniciado en modo terminal.")
    
    while True:
        # Opción de entrada por texto o voz
        print("\n📝 Opciones:")
        print("  1. Hablar (voz)")
        print("  2. Escribir (texto)")
        print("  3. Salir")
        
        opcion = input("\n👉 Selecciona (1/2/3): ").strip()
        
        if opcion == "1":
            comando = escuchar()
        elif opcion == "2":
            comando = input("💬 Escribe tu comando: ").strip().lower()
        elif opcion == "3":
            comando = "salir"
        else:
            print("❌ Opción inválida")
            continue
        
        if comando == "ERROR_MIC":
            print("❌ Error de micrófono detectado")
            continue
        
        if comando:
            respuesta, continuar = procesar_comando(comando)
            
            if respuesta:
                print(f"\n🤖 Aura: {respuesta}\n")
                hablar(respuesta)
            
            if not continuar:
                break
    
    print("\n👋 ¡Hasta pronto!")


def test_sistema():
    """
    Prueba rápida de los componentes del sistema
    """
    print("=" * 60)
    print("🧪 TEST DE SISTEMA")
    print("=" * 60)
    
    # Test 1: Text-to-Speech
    print("\n1️⃣  Test de síntesis de voz...")
    hablar("Probando sistema de voz")
    print("✅ Test completado")
    
    # Test 2: Speech-to-Text
    print("\n2️⃣  Test de reconocimiento de voz...")
    print("   (Di algo en 5 segundos)")
    comando = escuchar()
    if comando:
        print(f"✅ Reconocido: {comando}")
    else:
        print("⚠️  No se detectó voz")
    
    # Test 3: Procesamiento de comando
    print("\n3️⃣  Test de procesamiento...")
    respuesta, _ = procesar_comando("hola")
    print(f"✅ Respuesta: {respuesta[:50]}...")
    
    print("\n" + "=" * 60)
    print("🎉 Tests completados")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Aura - Asistente de IA")
    parser.add_argument("--terminal", action="store_true", help="Ejecutar en modo terminal")
    parser.add_argument("--test", action="store_true", help="Ejecutar tests del sistema")
    
    args = parser.parse_args()
    
    if args.test:
        test_sistema()
    elif args.terminal:
        modo_terminal()
    else:
        print("ℹ️  Ejecuta con --terminal para modo consola o --test para pruebas")
        print("   Para interfaz gráfica, ejecuta: python run.py")