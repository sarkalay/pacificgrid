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
        self.agent_kp = Keypair.from_base58_string(self.priv_key.strip())
        self.pub_key_str = os.getenv("PACIFICA_AGENT_PUBLIC_KEY")
        # Base URL ကို အောက်ပါအတိုင်း အတိအကျ ပြောင်းလဲပါ
        self.base_url = "https://api.pacifica.fi/api/v1" 

    def get_market_price(self, market_id):
        """Pacifica API မှ Mark Price ကို ရယူခြင်း"""
        try:
            # /info/prices endpoint သည် symbol အားလုံး၏ ဈေးနှုန်းကို ပြန်ပေးသည်
            url = f"{self.base_url}/info/prices"
            res = requests.get(url)
            
            if res.status_code == 200:
                data = res.json() # ၎င်းသည် list တစ်ခု ပြန်ပေးပါမည်
                # သက်ဆိုင်ရာ market_id (symbol) ကို ရှာဖွေခြင်း
                for item in data:
                    if item.get('symbol') == market_id:
                        # Grid Bot အတွက် 'mark' price ကို သုံးခြင်းက ပိုမို တည်ငြိမ်ပါသည်
                        return float(item.get('mark'))
                
                print(f"Error: {market_id} ကို Market list ထဲမှာ ရှာမတွေ့ပါ။")
                return None
            else:
                print(f"API Error: Status {res.status_code} at {url}")
                return None
        except Exception as e:
            print(f"Price Fetch Error: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """Order တင်ခြင်း logic"""
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

        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }

        # Order endpoint သည် /api/v1/order ဖြစ်သည်
        res = requests.post(f"{self.base_url}/order", json=payload, headers=headers)
        if res.status_code == 200:
            return res.json().get('order_id')
        else:
            print(f"Order Placement Failed: {res.text}")
            return None
