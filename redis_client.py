# redis_client.py
import redis
import json
from datetime import datetime
import logging # Import logging

logger = logging.getLogger(__name__) # Use logger for errors/info

from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# --- Redis Key Prefixes ---
ORDER_PREFIX = "food_orders:" # Key prefix for order hashes

# --- Initialize Redis Connection ---
try:
    redis_conn = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True # Important for handling strings easily
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
    """
    Adds or updates a food order in the hash for the current date.
    Uses user's display_name as the field, overwriting any previous order by that user for the day.
    """
    if not redis_conn:
        logger.error("Redis connection not available for add_or_update_order.")
        return False

    current_date_str = get_current_date_str()
    order_key = get_order_key_for_date(current_date_str)

    # Data to store as the value for the user's field in the hash
    order_value_data = {
        "food": food,
        "timestamp_iso": order_time.isoformat() # Store time as ISO string
    }
    try:
        # Convert the value data to a JSON string
        order_value_json = json.dumps(order_value_data)

        # HSET will add the field if new, or update the value if the field exists
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
        # HGETALL retrieves all fields and values from the hash
        # Returns a dict: { display_name: json_string_value, ... }
        raw_orders_hash = redis_conn.hgetall(order_key)

        orders_list = []
        if not raw_orders_hash:
             logger.info(f"No orders found in hash {order_key}")
             return []

        for display_name, order_value_json in raw_orders_hash.items():
            try:
                # Parse the JSON string value back into a dictionary
                order_value_data = json.loads(order_value_json)
                # Construct the final dictionary, adding the username back in
                order_entry = {
                    "username": display_name, # The field (key) from the hash
                    "food": order_value_data.get("food", "N/A"),
                    "timestamp_iso": order_value_data.get("timestamp_iso")
                }
                orders_list.append(order_entry)
            except json.JSONDecodeError:
                logger.warning(f"Could not decode JSON for user {display_name} in hash {order_key}: {order_value_json}")
            except Exception as inner_e:
                 logger.error(f"Error processing order for user {display_name} in hash {order_key}: {inner_e}")

        logger.info(f"Retrieved {len(orders_list)} orders from hash {order_key}")

        # Optional: Sort by timestamp for display consistency
        orders_list.sort(key=lambda x: datetime.fromisoformat(x['timestamp_iso']) if x.get('timestamp_iso') else datetime.min)

        return orders_list
    except Exception as e:
        logger.error(f"Error retrieving orders from Redis hash {order_key}: {e}", exc_info=True)
        return []