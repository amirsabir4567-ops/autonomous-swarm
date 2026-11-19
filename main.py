import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.first_name} ({user.id}) triggered /start command.")
    await update.message.reply_text(
        f"Hello {user.first_name}! Autonomous Swarm Agent Node is online, active, and monitoring commands."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    logger.info(f"Received message payload: {text}")
    await update.message.reply_text(f"Swarm Node processed command: '{text}'")

def main() -> None:
    if not TOKEN:
        logger.error("CRITICAL: TELEGRAM_BOT_TOKEN environment variable is missing!")
        return

    logger.info("Initializing Autonomous Swarm Agent Node with Telegram Integration...")
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Swarm worker loop entering active long-polling state...")
    application.run_polling()

if __name__ == "__main__":
    main()