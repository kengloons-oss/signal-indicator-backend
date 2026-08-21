import os
import requests

from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_message(message: str) -> bool:
    """
    Send a message to Telegram.

    Returns:
        True if successful
        False if failed
    """

    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is missing.")
        return False

    if not CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("ok"):
            print("✅ Telegram message sent successfully.")
            return True

        print("❌ Telegram returned an error:")
        print(data)

        return False

    except requests.exceptions.Timeout:
        print("❌ Telegram request timed out.")
        return False

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Telegram.")
        return False

    except requests.exceptions.HTTPError as error:
        print(f"❌ Telegram HTTP error: {error}")

        try:
            print(response.json())
        except Exception:
            pass

        return False

    except Exception as error:
        print(f"❌ Unexpected Telegram error: {error}")
        return False


if __name__ == "__main__":

    test_message = """
🚀 <b>RSI + MACD SIGNAL BOT</b>

Telegram connection successful! 🔥

The signal engine is ready.
"""

    send_message(test_message)