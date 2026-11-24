import requests

TG_TOKEN = "9090083594:AAEx5b0stvrE_74K8eQvIi2nOcBdZnStri8"
TG_CHAT = "5231255872"

try:
    msg = "🧪 TEST MESSAGE: Agar ye message aa raha hai, toh Telegram bot sahi kaam kar raha hai!"
    response = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": msg},
        timeout=10
    )
    if response.status_code == 200:
        print("✅ Test message sent successfully!")
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
