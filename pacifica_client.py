import os
import time
import json
import requests
from solders.keypair import Keypair
from dotenv import load_dotenv

load_dotenv()

class PacificaClient:
    def __init__(self):
        self.priv_key = os.getenv("PACIFICA_AGENT_PRIVATE_KEY")
        if not self.priv_key:
            raise ValueError("PACIFICA_AGENT_PRIVATE_KEY is missing in .env")
            
        self.agent_kp = Keypair.from_base58_string(self.priv_key.strip())
        self.pub_key_str = os.getenv("PACIFICA_AGENT_PUBLIC_KEY")
        # Base URL ကို ဤအတိုင်း အတိအကျ သုံးပါ
        self.base_url = "https://api.pacifica.fi/api/v1" 

    def get_market_price(self, market_id):
        """Pacifica API မှ Mark Price ကို ရယူခြင်း"""
        try:
            # /info/prices endpoint သည် symbol အားလုံး၏ ဈေးနှုန်းကို list အနေဖြင့် ပြန်ပေးသည်
            url = f"{self.base_url}/info/prices"
            res = requests.get(url, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                # Data list ထဲတွင် မိမိရှာဖွေနေသော symbol ရှိမရှိ စစ်ဆေးခြင်း
                for item in data:
                    if item.get('symbol') == market_id:
                        # Grid Trading အတွက် mark price က ပိုမို တည်ငြိမ်ပါသည်
                        return float(item.get('mark'))
                
                print(f"Error: {market_id} ကို Market list ထဲမှာ ရှာမတွေ့ပါ။")
                return None
            else:
                print(f"API Error: Status {res.status_code} at {url}")
                return None
        except Exception as e:
            print(f"Price Fetch Exception: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """SDK ပါ create_limit_order logic အတိုင်း အော်ဒါတင်ခြင်း"""
        timestamp = int(time.time() * 1000)
        
        # SDK payload format အတိုင်း ပြင်ဆင်ခြင်း
        payload = {
            "agent": self.pub_key_str,
            "market": market_id,
            "side": side.upper(),
            "price": str(price),
            "size": str(size),
            "type": "LIMIT",
            "timestamp": timestamp
        }

        # JSON payload ကို Sign လုပ်ခြင်း
        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }

        try:
            # Order endpoint သို့ POST ပို့ခြင်း
            res = requests.post(f"{self.base_url}/order", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                print(f"Success: {side} order placed at {price}")
                return res.json().get('order_id')
            else:
                print(f"Placement Error: {res.text}")
                return None
        except Exception as e:
            print(f"Request Error: {e}")
            return None

    def check_order_status(self, order_id):
        """အော်ဒါ status စစ်ဆေးခြင်း"""
        try:
            res = requests.get(f"{self.base_url}/order/{order_id}")
            if res.status_code == 200:
                return res.json().get('status')
            return "UNKNOWN"
        except: return "UNKNOWN"
