import os
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL de nuestra API local FastAPI
API_URL = "http://localhost:8000/chat"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    welcome_message = (
        "¡Hola! 👋 Soy BravoBot, tu asistente inteligente para aspirantes de la "
        "I.U. Pascual Bravo. 🎓\n\n"
        "Puedes preguntarme sobre inscripciones, programas académicos, "
        "costos, o cualquier otra duda que tengas.\n\n"
        "¿En qué te puedo ayudar hoy?"
    )
    await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el mensaje del usuario a la API de BravoBot y devuelve la respuesta."""
    user_message = update.message.text
    # Usamos el chat_id de Telegram como session_id para mantener el historial
    chat_id = str(update.message.chat_id)
    
    # Mostrar el estado "Escribiendo..." en Telegram
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        # Hacemos la petición a nuestra API local
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                API_URL,
                json={"query": user_message, "session_id": chat_id}
            )
            response.raise_for_status()
            data = response.json()
            
            # Obtener la respuesta generada
            respuesta_bot = data.get("respuesta", "Lo siento, hubo un error procesando la respuesta.")
            
            # Enviar la respuesta al usuario en Telegram
            await update.message.reply_text(respuesta_bot)
            
    except httpx.ConnectError:
        logger.error("No se pudo conectar a la API. ¿Está corriendo uvicorn en el puerto 8000?")
        await update.message.reply_text("Lo siento, el cerebro de BravoBot está desconectado en este momento. 🔌")
    except Exception as e:
        logger.error(f"Error comunicándose con la API: {e}")
        await update.message.reply_text("Lo siento, estoy teniendo problemas técnicos temporales. 🛠️ Intenta de nuevo más tarde.")

def main():
    if not TOKEN:
        logger.error("No se encontró TELEGRAM_BOT_TOKEN en el archivo .env. ¡Asegúrate de agregarlo!")
        return
        
    # Inicializar la aplicación del bot
    application = Application.builder().token(TOKEN).build()

    # Registrar los manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Iniciar el bot
    logger.info("Bot de Telegram iniciado y escuchando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
