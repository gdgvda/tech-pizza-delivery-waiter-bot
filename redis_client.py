# redis_client.py
import redis
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# --- Redis Key Prefixes ---
ORDER_PREFIX = "food_orders:"
# --- Prefix for user message sorted sets ---
MESSAGES_USER_PREFIX = "messages:user:"

# --- Initialize Redis Connection ---
try:
    redis_conn = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_conn.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Error connecting to Redis: {e}")
    redis_conn = None

# --- Helper Functions ---
def get_current_date_str() -> str:
    return datetime.today().strftime('%Y-%m-%d')

def get_order_key_for_date(date_str: str) -> str:
    return f"{ORDER_PREFIX}{date_str}"

# --- NEW: Message Storage Helper ---
def get_messages_key_for_user(user_id: int) -> str:
    """Constructs the Redis Sorted Set key for a user's messages."""
    return f"{MESSAGES_USER_PREFIX}{user_id}"
# --- END NEW ---

# --- Order Functions (Keep as before) ---
def add_or_update_order(display_name: str, food: str, order_time: datetime) -> bool:
    if not redis_conn: return False
    current_date_str = get_current_date_str()
    order_key = get_order_key_for_date(current_date_str)
    order_value_data = {"food": food, "timestamp_iso": order_time.isoformat()}
    try:
        order_value_json = json.dumps(order_value_data)
        redis_conn.hset(order_key, display_name, order_value_json)
        logger.info(f"Stored/Updated order for {display_name} ({food}) for date {current_date_str}")
        return True
    except Exception as e:
        logger.error(f"Error HSET order {order_key} for user {display_name}: {e}", exc_info=True)
        return False

def get_orders_for_day(date_str: str) -> list[dict]:
    if not redis_conn: return []
    order_key = get_order_key_for_date(date_str)
    try:
        raw_orders_hash = redis_conn.hgetall(order_key)
        orders_list = []
        if not raw_orders_hash: return []
        for display_name, order_value_json in raw_orders_hash.items():
            try:
                order_value_data = json.loads(order_value_json)
                order_entry = {
                    "username": display_name,
                    "food": order_value_data.get("food", "N/A"),
                    "timestamp_iso": order_value_data.get("timestamp_iso")
                }
                orders_list.append(order_entry)
            except Exception as inner_e:
                 logger.warning(f"Error parsing order JSON for user {display_name}: {inner_e}")
        orders_list.sort(key=lambda x: datetime.fromisoformat(x['timestamp_iso']) if x.get('timestamp_iso') else datetime.min)
        return orders_list
    except Exception as e:
        logger.error(f"Error HGETALL orders {order_key}: {e}", exc_info=True)
        return []

def delete_order_for_user(display_name: str, date_str: str) -> bool:
    if not redis_conn: return False
    order_key = get_order_key_for_date(date_str)
    try:
        result = redis_conn.hdel(order_key, display_name)
        return result > 0
    except Exception as e:
        logger.error(f"Error HDEL order {order_key} for user {display_name}: {e}", exc_info=True)
        return False

def store_user_message(user_id: int, message_text: str, message_time: datetime) -> bool:
    """Stores a user's message in their sorted set using timestamp as score."""
    if not redis_conn:
        logger.error("Redis connection not available for store_user_message.")
        return False

    messages_key = get_messages_key_for_user(user_id)
    timestamp_score = message_time.timestamp() # Use Unix float timestamp for score

    try:
        # ZADD key score member [score member ...]
        # If message_text (member) already exists, its score (timestamp) is updated.
        # This naturally handles storing the same message text multiple times if sent at different times.
        redis_conn.zadd(messages_key, {message_text: timestamp_score})
        # logger.debug(f"Stored message for user {user_id} in key {messages_key}") # Maybe too verbose
        return True
    except Exception as e:
        logger.error(f"Error ZADD message to Redis key {messages_key} for user {user_id}: {e}", exc_info=True)
        return False
# --- END NEW MESSAGE STORAGE FUNCTION ---

# May be useful for new features
# --- (Optional) Function to retrieve messages - NOT USED BY ANY COMMAND CURRENTLY ---
def get_user_messages_desc(user_id: int, count: int = 100) -> list[tuple[str, datetime]]:
    """
    Retrieves the latest 'count' messages for a user, sorted DESC by time.
    Returns list of tuples: (message_text, message_datetime)
    """
    if not redis_conn:
        logger.error("Redis connection not available for get_user_messages_desc.")
        return []

    messages_key = get_messages_key_for_user(user_id)
    try:
        # ZREVRANGE key start stop [WITHSCORES]
        # Get members and scores, highest score (latest time) first
        results = redis_conn.zrevrange(messages_key, 0, count - 1, withscores=True)
        # Results look like: [ (member1, score1), (member2, score2), ... ]

        messages_list = []
        for member, score in results:
            message_text = member
            timestamp_score = score
            try:
                # Convert Unix timestamp score back to datetime
                message_datetime = datetime.fromtimestamp(timestamp_score)
                messages_list.append((message_text, message_datetime))
            except Exception as dt_e:
                 logger.warning(f"Could not convert timestamp {timestamp_score} for user {user_id}: {dt_e}")
                 # Optionally append with None or skip
                 # messages_list.append((message_text, None))


        logger.info(f"Retrieved {len(messages_list)} messages for user {user_id} from key {messages_key}")
        return messages_list

    except Exception as e:
        logger.error(f"Error ZREVRANGE messages from Redis key {messages_key} for user {user_id}: {e}", exc_info=True)
        return []
# --- END Optional Retrieval Function ---