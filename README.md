# Telegram Daily Food Order Bot 🍕

A Python-based Telegram bot designed for group members to place food orders easily within a group chat. Each user can place or update their order once per day. It uses Redis for data storage and Docker/Docker Compose for simple deployment.

## Features

*   **Daily Ordering:** Users can place orders any day using the `/food <food choice>` command.
*   **Order Replacement:** If a user issues the `/food` command multiple times on the same day, their previous order for that day is replaced with the new one. Only the latest order per user per day is stored.
*   **Group Summary:** Anyone can view the collective list of the latest orders for the *current* day using the `/summary` command.
*   **User Identification:** Identifies users by `@username` if available, otherwise uses their `first_name`, falling back to `User ID`.
*   **Redis Storage:** Stores orders in Redis Hashes, keyed by date (`YYYY-MM-DD`). Each user's display name is a field within the hash for that day.
*   **Dockerized:** Includes a `Dockerfile` and `docker-compose.yml` for straightforward setup and deployment with Redis included.
*   **Configurable:** Easily configure the bot token and Redis settings via environment variables (`.env`).

## Technology Stack

*   **Language:** Python 3.12+
*   **Telegram Library:** `python-telegram-bot` (v21.1)
*   **Database:** Redis (via `redis-py` >= 5.0.0)
*   **Configuration:** `python-dotenv`
*   **Containerization:** Docker & Docker Compose

## Prerequisites

*   Docker ([Install Guide](https://docs.docker.com/engine/install/))
*   Docker Compose (v1.27+ or V2 - usually included with Docker Desktop)
*   Git (for cloning the repository)
*   A Telegram Bot Token obtained from [@BotFather](https://t.me/BotFather) on Telegram.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory by copying `.env-sample` or creating it manually. Add the following variables:

    ```dotenv
    # .env
    TELEGRAM_BOT_TOKEN="YOUR_ACTUAL_TELEGRAM_BOT_TOKEN"

    # Redis Configuration for Docker Compose
    REDIS_HOST="redis" # Use the service name from docker-compose.yml
    REDIS_PORT="6379"
    REDIS_DB="0"
    # REDIS_PASSWORD="your_strong_redis_password" # Uncomment and set if you configured a password in docker-compose.yml
    ```
    *   **Replace `"YOUR_ACTUAL_TELEGRAM_BOT_TOKEN"`** with the token you got from BotFather.
    *   Ensure `REDIS_HOST` is set to `redis` when using the provided `compose.yml`.

3.  **(Recommended) Generate/Update Dependency Lock File:**
    Ensure your `requirements.txt` matches the dependencies in `pyproject.toml`.
    *   **Using `uv` (Recommended):**
        ```bash
        # Install uv if you don't have it: pip install uv
        uv pip compile pyproject.toml --output-file requirements.txt
        # Optionally sync your environment: uv pip sync requirements.txt
        ```
    *   **Using `pip-tools`:**
        ```bash
        # Install pip-tools if you don't have it: pip install pip-tools
        pip-compile pyproject.toml --output-file=requirements.txt --resolver=backtracking
        # Optionally sync your environment: pip-sync requirements.txt
        ```

## Running the Bot (using Docker Compose)

This is the recommended method as it manages both the bot and the Redis database container.

1.  **Build the Docker Image:**
    *(This builds the image based on the Dockerfile and requirements.txt)*
    ```bash
    docker compose build
    ```

2.  **Start the Services:**
    *(This starts the bot and Redis containers in the background)*
    ```bash
    docker compose up -d
    ```

3.  **Check Logs (Optional):**
    *(View the bot's output/logs)*
    ```bash
    docker compose logs -f bot
    ```
    *(View Redis logs)*
    ```bash
    docker compose logs -f redis
    ```

4.  **Stop the Services:**
    ```bash
    docker compose down
    ```
    *(To stop and remove containers/networks. Use `docker compose down -v` to also remove the Redis data volume, effectively clearing all past order history)*

## Bot Usage

Add the bot to your Telegram group chat. Participants can interact with the following commands:

*   `/start`: Displays a welcome message.
*   `/help`: Shows available commands and usage instructions.
*   `/food <food choice>`: Places or updates your order for the **current day**. If you've already ordered today, this command replaces your previous choice.
    *   Example: `/food Pepperoni Pizza`
*   `/reset`: Removes your food order entry for the **current day**. Use this if you decide not to order after all.
*   `/summary`: The bot posts a list of the latest food orders placed by everyone for the **current day** in the group chat, sorted approximately by time.  

## Customization

*   **User Identification:** The logic for choosing `@username`, `first_name`, or `User ID` is in `main.py` within the `get_display_name` function.
*   **Redis Keys:** The date-based key format (`food_orders:YYYY-MM-DD`) is defined in `redis_client.py`.
*   **Data Persistence:** Orders are stored in Redis under daily keys. Old data persists. To clear *all* history, stop the containers and remove the volume using `docker compose down -v`. Specific days could be deleted manually using Redis commands if needed.

## Contributing

Contributions, issues, and feature requests are welcome. Please open an issue to discuss significant changes beforehand.

## License

[MIT](LICENSE) <!-- Make sure you have a LICENSE file, e.g., containing the MIT license text -->