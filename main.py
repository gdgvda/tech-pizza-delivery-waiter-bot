# main.py
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, User
from telegram.ext import (
    Application,
    CommandHandler,
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

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    user = update.effective_user
    display_name = get_display_name(user)
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I'm the Food Order Bot 🍕."
        "\nUse /help to see what I can do.",
        reply_markup=None,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message explaining commands."""
    help_text = "Here's how to use me:\n\n"
    help_text += "➡️ Place or update your order for today: `/food <your food choice>`\n"
    help_text += "   Example: `/food Pizza Margherita`\n"
    help_text += "   *Note:* Using /food again today replaces your previous order.\n\n"
    # --- Use /reset in help text ---
    help_text += "🗑️ Remove your order for today: `/reset`\n\n"
    # --- End change ---
    help_text += "📋 See all orders placed *today*: `/summary`\n\n"
    help_text += "ℹ️ Show this help message: /help"

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def food_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /food command to place or update an order for the current day."""
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

    logger.info(f"User {user.id} ({display_name_to_store}) in chat {chat.id} submitting order '{food_name}' for today.")

    success = rc.add_or_update_order(
        display_name=display_name_to_store,
        food=food_name,
        order_time=order_time
    )

    if success:
        await update.message.reply_text(f"✅ Got it, {user.first_name}! Your order for today is now: {food_name}")
    else:
        await update.message.reply_text("😥 Sorry, there was an error saving/updating your order. Please try again.")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /summary command to show all orders for the current day."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat: return

    logger.info(f"User {user.id} ({get_display_name(user)}) requested /summary in chat {chat.id}.")

    current_date_str = rc.get_current_date_str()
    orders = rc.get_orders_for_day(current_date_str)

    if not orders:
        await update.message.reply_text(f"🤔 No food orders placed yet for today ({current_date_str}).")
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
            except (ValueError, TypeError):
                 pass

        summary_text += f"{i+1}. **{food_item}** - _{stored_name}_{time_str}\n"

    summary_text += f"\n--- Total Orders: {len(orders)} ---"

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=summary_text,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Sent order summary for {current_date_str} to chat {chat.id}")
    except Exception as e:
        logger.error(f"Failed send summary for {current_date_str} to chat {chat.id}: {e}", exc_info=True)
        await update.message.reply_text("😥 Sorry, I couldn't send the order summary here.")


# --- RENAME HANDLER FUNCTION for clarity ---
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
# --- END RENAME HANDLER FUNCTION ---
    """Handles the /reset command to remove the user's order for the day."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat: return

    display_name = get_display_name(user)
    current_date_str = rc.get_current_date_str()

    # --- Log the correct command name ---
    logger.info(f"User {user.id} ({display_name}) in chat {chat.id} requested /reset for today ({current_date_str}).")
    # --- End log change ---

    deleted = rc.delete_order_for_user(display_name, current_date_str)

    if deleted:
        await update.message.reply_text(f"🗑️ Okay, {user.first_name}, I've removed your food order for today.")
    else:
        await update.message.reply_text(f"🤔 {user.first_name}, I couldn't find an order for you today to remove.")


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

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("food", food_command))
    application.add_handler(CommandHandler("summary", summary_command))
    # --- REGISTER HANDLER with new command name and function name ---
    application.add_handler(CommandHandler("reset", reset_command))
    # --- END REGISTER HANDLER CHANGE ---


    logger.info("Starting bot polling...")
    print("Food Order Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Bot stopped.")

if __name__ == "__main__":
    main()