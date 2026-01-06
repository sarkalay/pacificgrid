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
        # Documentation အရ Base URL အမှန်
        self.base_url = "https://api.pacifica.fi/api/v1" 

    def get_market_price(self, market_id):
        """Pacifica API မှ Mark Price ကို စနစ်တကျ ရယူခြင်း"""
        try:
            # /info/prices သည် market အားလုံး၏ ဈေးနှုန်းကို list အနေဖြင့် ပြန်ပေးသည်
            url = f"{self.base_url}/info/prices"
            res = requests.get(url, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                
                # API က List အနေနဲ့ ပြန်လာတာကို Loop ပတ်ပြီး ရှာခြင်း
                if isinstance(data, list):
                    for item in data:
                        # symbol အခေါ်အဝေါ် တိုက်စစ်ခြင်း
                        if item.get('symbol') == market_id:
                            # Grid Bot အတွက် 'mark' price သည် အသင့်တော်ဆုံးဖြစ်သည်
                            price = item.get('mark') or item.get('last')
                            return float(price) if price else None
                
                print(f"Error: {market_id} ကို Market list ထဲမှာ ရှာမတွေ့ပါ။")
                return None
            else:
                print(f"API Error {res.status_code}: {res.text}")
                return None
        except Exception as e:
            print(f"Price Fetch Exception: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """Authenticated Order Placement"""
        timestamp = int(time.time() * 1000)
        
        payload = {
            "agent": self.pub_key_str,
            "market": market_id,
            "side": side.upper(),
            "price": str(price),
            "size": str(size),
            "type": "LIMIT",
            "timestamp": timestamp
        }

        # SDK/Docs ပါ logic အတိုင်း Signature ပြုလုပ်ခြင်း
        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }

        try:
            # Order endpoint သည် /api/v1/order ဖြစ်သည်
            res = requests.post(f"{self.base_url}/order", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                print(f"Success: {side} order placed at {price}")
                return res.json().get('order_id')
            else:
                print(f"Placement Error: {res.text}")
                return None
        except Exception as e:
            print(f"Order Connection Error: {e}")
            return None

    def check_order_status(self, order_id):
        """Order Status စစ်ဆေးခြင်း"""
        try:
            res = requests.get(f"{self.base_url}/order/{order_id}")
            if res.status_code == 200:
                return res.json().get('status')
            return "UNKNOWN"
        except: return "UNKNOWN"
