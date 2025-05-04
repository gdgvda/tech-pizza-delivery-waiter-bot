# redis_client.py
import redis
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# --- Redis Key Prefixes ---
ORDER_PREFIX = "food_orders:"

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
    """Gets the current date string (YYYY-MM-DD)."""
    return datetime.today().strftime('%Y-%m-%d')

def get_order_key_for_date(date_str: str) -> str:
    """Constructs the Redis HASH key for orders on a specific date."""
    return f"{ORDER_PREFIX}{date_str}"

# --- Core Functions ---
def add_or_update_order(display_name: str, food: str, order_time: datetime) -> bool:
    """Adds or updates a food order in the hash for the current date."""
    if not redis_conn:
        logger.error("Redis connection not available for add_or_update_order.")
        return False
    current_date_str = get_current_date_str()
    order_key = get_order_key_for_date(current_date_str)
    order_value_data = {
        "food": food,
        "timestamp_iso": order_time.isoformat()
    }
    try:
        order_value_json = json.dumps(order_value_data)
        redis_conn.hset(order_key, display_name, order_value_json)
        logger.info(f"Stored/Updated order for {display_name} ({food}) for date {current_date_str}")
        return True
    except Exception as e:
        logger.error(f"Error adding/updating order to Redis hash {order_key} for user {display_name}: {e}", exc_info=True)
        return False

def get_orders_for_day(date_str: str) -> list[dict]:
    """Gets all orders stored in the hash for a specific date."""
    if not redis_conn:
        logger.error("Redis connection not available for get_orders_for_day.")
        return []
    order_key = get_order_key_for_date(date_str)
    try:
        raw_orders_hash = redis_conn.hgetall(order_key)
        orders_list = []
        if not raw_orders_hash:
            logger.info(f"No orders found in hash {order_key}")
            return []
        for display_name, order_value_json in raw_orders_hash.items():
            try:
                order_value_data = json.loads(order_value_json)
                order_entry = {
                    "username": display_name,
                    "food": order_value_data.get("food", "N/A"),
                    "timestamp_iso": order_value_data.get("timestamp_iso")
                }
                orders_list.append(order_entry)
            except json.JSONDecodeError:
                logger.warning(f"Could not decode JSON for user {display_name} in hash {order_key}: {order_value_json}")
            except Exception as inner_e:
                logger.error(f"Error processing order for user {display_name} in hash {order_key}: {inner_e}")

        logger.info(f"Retrieved {len(orders_list)} orders from hash {order_key}")
        orders_list.sort(key=lambda x: datetime.fromisoformat(x['timestamp_iso']) if x.get('timestamp_iso') else datetime.min)
        return orders_list
    except Exception as e:
        logger.error(f"Error retrieving orders from Redis hash {order_key}: {e}", exc_info=True)
        return []

# --- NEW FUNCTION ---
def delete_order_for_user(display_name: str, date_str: str) -> bool:
    """
    Deletes the order (field) for a specific user from the hash for a given date.
    Returns True if an order was found and deleted, False otherwise.
    """
    if not redis_conn:
        logger.error("Redis connection not available for delete_order_for_user.")
        return False

    order_key = get_order_key_for_date(date_str)
    try:
        # HDEL returns the number of fields that were removed.
        result = redis_conn.hdel(order_key, display_name)
        if result > 0:
            logger.info(f"Deleted order for user {display_name} from hash {order_key}")
            return True
        else:
            logger.info(f"No order found for user {display_name} in hash {order_key} to delete.")
            return False
    except Exception as e:
        logger.error(f"Error deleting order from Redis hash {order_key} for user {display_name}: {e}", exc_info=True)
        return False
# --- END NEW FUNCTION ---