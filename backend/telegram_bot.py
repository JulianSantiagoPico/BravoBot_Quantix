import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

sys.path.insert(0, str(Path(__file__).parent))
from logger import get_logger, setup_logging

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configurar logging centralizado
setup_logging()
logger = get_logger("bravobot.telegram")

# URL de nuestra API local FastAPI
API_URL = os.getenv("API_URL", "http://localhost:8000/chat")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    if update.message is None:
        return

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
    if update.message is None or update.message.text is None:
        return

    user_message = update.message.text
    chat_id = str(update.message.chat_id)
    username = (
        update.message.from_user.username or update.message.from_user.first_name or "?"
    )

    logger.info(
        "[TELEGRAM] ← %s (chat=%s): %.100s",
        username,
        chat_id,
        user_message,
    )

    # Mostrar el estado "Escribiendo..." en Telegram
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")

    try:
        # Hacemos la petición a nuestra API local
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                API_URL, json={"query": user_message, "session_id": chat_id}
            )
            response.raise_for_status()
            data = response.json()

            respuesta_bot = data.get(
                "respuesta", "Lo siento, hubo un error procesando la respuesta."
            )

            logger.info(
                "[TELEGRAM] → %s (chat=%s): %d chars | intent=%s",
                username,
                chat_id,
                len(respuesta_bot),
                data.get("intent", "?"),
            )

            await update.message.reply_text(respuesta_bot)

    except httpx.ConnectError:
        logger.error(
            "[TELEGRAM] No se pudo conectar a la API %s para chat=%s",
            API_URL,
            chat_id,
        )
        await update.message.reply_text(
            "Lo siento, el cerebro de BravoBot está desconectado en este momento. 🔌"
        )
    except Exception as e:
        logger.error("[TELEGRAM] Error para chat=%s: %s", chat_id, e)
        await update.message.reply_text(
            "Lo siento, estoy teniendo problemas técnicos temporales. 🛠️ Intenta de nuevo más tarde."
        )


def main():
    if not TOKEN:
        logger.error(
            "No se encontró TELEGRAM_BOT_TOKEN en el archivo .env. ¡Asegúrate de agregarlo!"
        )
        return

    # Inicializar la aplicación del bot
    application = Application.builder().token(TOKEN).build()

    # Registrar los manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Iniciar el bot
    logger.info("Bot de Telegram iniciado y escuchando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
