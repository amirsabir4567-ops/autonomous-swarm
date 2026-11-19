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

# Configure structured logging for cloud tracking (Render/Oracle Cloud logs)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fetch Telegram Token securely from environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command from Telegram."""
    user = update.effective_user
    logger.info(f"User {user.first_name} ({user.id}) triggered /start command.")
    await update.message.reply_text(
        f"Hello {user.first_name}! Autonomous Swarm Agent Node is online, active, and monitoring commands."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general text inputs sent to the autonomous swarm control channel."""
    text = update.message.text
    logger.info(f"Received message payload: {text}")
    await update.message.reply_text(f"Swarm Node processed command: '{text}'")

def main() -> None:
    """Initialize and run the autonomous swarm control node."""
    if not TOKEN:
        logger.error("CRITICAL: TELEGRAM_BOT_TOKEN environment variable is missing!")
        return

    logger.info("Initializing Autonomous Swarm Agent Node with Telegram Integration...")
    
    # Build the Telegram application using python-telegram-bot v20+
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Swarm worker loop entering active long-polling state...")
    
    # Start polling for Telegram updates continuously
    application.run_polling()

if __name__ == "__main__":
    main()