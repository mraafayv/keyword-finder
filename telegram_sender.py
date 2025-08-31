import os
import requests



def send_message(token: str, chat_id: str, text: str, *, html: bool = True) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    formatted_text = "\n".join(f"{i}- {u}" for i, u in enumerate(text, 1))

    msg = (
    "<b>Job Alert</b>\n\n"
    "Check out these jobs with bonuses:\n\n"
    f"{formatted_text}"
    )

    payload = {
        "chat_id": chat_id,
        "text": msg,
        "disable_web_page_preview": True,
    }
    if html:
        payload["parse_mode"] = "HTML"

    resp = requests.post(url, json=payload, timeout=15)

    # Show useful error info if something goes wrong
    try:
        data = resp.json()
    except ValueError:
        resp.raise_for_status()

    if not data.get("ok", False):
        raise RuntimeError(f"Telegram error: {data.get('description')}")

    print(f"Sent. Message ID: {data['result']['message_id']}")

# if __name__ == "__main__":
#     send_message(TOKEN, CHAT_ID, TEXT)

