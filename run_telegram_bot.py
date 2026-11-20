import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://swarm_admin:secure_local_password_change_me@postgres:5432/commerce_swarm_db")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                platform VARCHAR(100),
                payload TEXT,
                status VARCHAR(50) DEFAULT 'STAGED',
                retry_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database schema verified/initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def is_admin(update: Update) -> bool:
    if not update.effective_user:
        return False
    return str(update.effective_user.id) == str(ADMIN_CHAT_ID)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("Unauthorized access.")
        return
    await update.message.reply_text("🤖 **Autonomous Swarm Core Online (PostgreSQL Powered)**\n\nCommands:\n/status - View task queue\n/add_task <platform> <payload>", parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status;")
        stats = cursor.fetchall()
        cursor.close()
        conn.close()
        
        status_msg = "📊 *Swarm Queue Status (PostgreSQL):*\n"
        for row in stats:
            status_msg += f"- {row[0]}: {row[1]}\n"
        if not stats:
            status_msg += "No tasks found in the database yet."
        await update.message.reply_text(status_msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Database error: {e}")

async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("❌ Usage format: `/add_task <platform> <payload>`", parse_mode="Markdown")
        return
    
    platform = args[0]
    payload = " ".join(args[1:])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Initialized as 'STAGED' so the worker loop won't pick it up automatically before approval
        cursor.execute(
            "INSERT INTO tasks (platform, payload, status, retry_count) VALUES (%s, %s, 'STAGED', 0) RETURNING id;",
            (platform, payload)
        )
        task_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Run", callback_data=f"approve_{task_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{task_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📥 *Task Staged for Review* (ID: #{task_id})\nPlatform: *{platform}*\nPayload: {payload}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to enqueue task: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        await query.answer("Unauthorized.", show_alert=True)
        return
    await query.answer()
    
    try:
        action, task_id = query.data.split("_")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if action == "approve":
            # Flips status to 'PENDING' so the worker loop can pull and process it
            cursor.execute("UPDATE tasks SET status = 'PENDING' WHERE id = %s;", (task_id,))
            conn.commit()
            await query.edit_message_text(text=f"✅ Task #{task_id} Approved and Queued for Execution.")
        elif action == "reject":
            cursor.execute("UPDATE tasks SET status = 'REJECTED' WHERE id = %s;", (task_id,))
            conn.commit()
            await query.edit_message_text(text=f"❌ Task #{task_id} Rejected.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Callback error: {e}")

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("TELEGRAM_BOT_TOKEN is missing!")
        exit(1)
        
    init_db()
    logger.info("=== STARTING TELEGRAM CONTROL DAEMON ===")
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("add_task", add_task_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.run_polling()