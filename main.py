# main.py
import logging
import os
# import io # No longer needed as /backup removed
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, User # , InputFile # No longer needed
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler, # Keep MessageHandler
    filters, # Keep filters
    ContextTypes,
    ApplicationBuilder
)
from telegram.constants import ParseMode

# --- Load Environment Variables ---
load_dotenv()

# --- Now import local modules ---
from config import TELEGRAM_BOT_TOKEN
import redis_client as rc

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_display_name(user: User) -> str:
    """Gets the best available identifier (Priority: @username > first_name > User ID)."""
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    else:
        return f"User ID {user.id}"

# --- Command Handlers (start, help, food, summary, reset remain the same) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I'm the Food Order Bot 🍕."
        "\nUse /help to see what I can do.",
        reply_markup=None,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message explaining commands. DOES NOT MENTION message logging."""
    # --- No changes needed here, message logging is hidden ---
    help_text = "Here's how to use me:\n\n"
    help_text += "➡️ Place or update your order for today: `/food <your food choice>`\n"
    help_text += "   Example: `/food Pizza Margherita`\n"
    help_text += "   *Note:* Using /food again today replaces your previous order.\n\n"
    help_text += "🗑️ Remove your order for today: `/reset`\n\n"
    help_text += "📋 See all orders placed *today*: `/summary`\n\n"
    help_text += "ℹ️ Show this help message: /help"
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def food_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat: return
    if not context.args:
        await update.message.reply_text("Please tell me what food you want! Usage: `/food <food name>`")
        return
    food_name = " ".join(context.args).strip()
    if not food_name:
        await update.message.reply_text("Looks like you didn't specify any food. Usage: `/food <food name>`")
        return
    display_name_to_store = get_display_name(user)
    order_time = datetime.now()
    logger.info(f"User {user.id} ({display_name_to_store}) submitting order '{food_name}'")
    success = rc.add_or_update_order(display_name=display_name_to_store, food=food_name, order_time=order_time)
    if success:
        await update.message.reply_text(f"✅ Got it, {user.first_name}! Your order for today is now: {food_name}")
    else:
        await update.message.reply_text("😥 Error saving/updating order.")

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat: return
    logger.info(f"User {user.id} ({get_display_name(user)}) requested /summary.")
    current_date_str = rc.get_current_date_str()
    orders = rc.get_orders_for_day(current_date_str)
    if not orders:
        await update.message.reply_text(f"🤔 No orders placed yet for today ({current_date_str}).")
        return
    summary_text = f"--- 🍕 Food Orders for {current_date_str} ---\n\n"
    for i, order in enumerate(orders):
        stored_name = order.get('username', 'Unknown User')
        food_item = order.get('food', 'N/A')
        timestamp_str = order.get('timestamp_iso')
        time_str = ""
        if timestamp_str:
            try:
                dt_obj = datetime.fromisoformat(timestamp_str)
                time_str = f" ({dt_obj.strftime('%H:%M')})"
            except: pass
        summary_text += f"{i+1}. **{food_item}** - _{stored_name}_{time_str}\n"
    summary_text += f"\n--- Total Orders: {len(orders)} ---"
    try:
        await context.bot.send_message(chat_id=chat.id, text=summary_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Failed send summary: {e}", exc_info=True)
        await update.message.reply_text("😥 Error sending summary.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat: return
    display_name = get_display_name(user)
    current_date_str = rc.get_current_date_str()
    logger.info(f"User {user.id} ({display_name}) requested /reset.")
    deleted = rc.delete_order_for_user(display_name, current_date_str)
    if deleted:
        await update.message.reply_text(f"🗑️ Okay, {user.first_name}, removed your order for today.")
    else:
        await update.message.reply_text(f"🤔 {user.first_name}, couldn't find an order for you today.")


async def message_store_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles regular text messages to backup them using user_id as key."""
    user = update.effective_user
    message = update.effective_message
    # Basic checks: Must have user, message, text, and not be a command
    if not user or not message or not message.text or message.text.startswith('/'):
        return

    # Only store messages from groups or supergroups
    if message.chat.type not in ['group', 'supergroup']:
        return

    # Use user.id for the key, text for the value, and message.date for the score
    user_id = user.id
    message_text = message.text
    # Use message.date (timezone-aware UTC datetime from Telegram)
    message_time = message.date

    # logger.debug(f"Attempting to store message from user {user_id} in chat {message.chat.id}")

    success = rc.store_user_message(
        user_id=user_id,
        message_text=message_text,
        message_time=message_time
    )
    if not success:
        logger.warning(f"Failed to store message for user {user_id} from chat {message.chat.id}")
# --- END UPDATED MESSAGE HANDLER ---

# --- REMOVED backup_command and send_backup_as_file functions ---

# --- Main Bot Execution ---
def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("FATAL: TELEGRAM_BOT_TOKEN not found!")
        print("\nError: TELEGRAM_BOT_TOKEN is missing.\n")
        return

    if not rc.redis_conn:
        logger.error("FATAL: Could not connect to Redis.")
        print("\nError: Failed to connect to Redis.\n")
        return
    else:
        logger.info("Redis connection successful.")

    builder = Application.builder().token(token)
    application = builder.build()

    # Register Command Handlers 
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("food", food_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("reset", reset_command))

    # --- REGISTER MESSAGE HANDLER (must be after commands) ---
    # Handle non-command text messages in groups/supergroups for backup
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (filters.ChatType.GROUPS),
        message_store_handler
    ))
    # --- END REGISTER MESSAGE HANDLER ---

    logger.info("Starting bot polling...")
    print("Food Order Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES) # Need ALL_TYPES for MessageHandler
    print("Bot stopped.")

if __name__ == "__main__":
    main()