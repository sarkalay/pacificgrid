import os
import time
import json
import requests
from solders.keypair import Keypair
from dotenv import load_dotenv

load_dotenv()

class PacificaClient:
    def __init__(self):
        # Environment variables မှ key များကို ရယူခြင်း
        self.priv_key = os.getenv("PACIFICA_AGENT_PRIVATE_KEY")
        if not self.priv_key:
            raise ValueError("PACIFICA_AGENT_PRIVATE_KEY ကို .env မှာ ရှာမတွေ့ပါ။")
            
        self.agent_kp = Keypair.from_base58_string(self.priv_key.strip())
        self.pub_key_str = os.getenv("PACIFICA_AGENT_PUBLIC_KEY")
        
        # Pacifica Documentation အရ Base URL
        # အကယ်၍ error ထပ်တက်ပါက https://api.pacifica.fi/api/v1 သို့ ပြောင်းကြည့်ပါ
        self.base_url = "https://api.pacifica.fi/v1" 

    def get_market_price(self, market_id):
        """Pacifica API မှ Mark Price သို့မဟုတ် Last Price ကို စနစ်တကျ ရယူခြင်း"""
        try:
            # SDK နှင့် Docs အရ ticker endpoint ကို သုံးသည်
            url = f"{self.base_url}/ticker?market={market_id}"
            res = requests.get(url, timeout=10)
            
            # Response က JSON ဟုတ်မဟုတ် စစ်ဆေးခြင်း
            if res.status_code == 200:
                try:
                    data = res.json()
                except ValueError:
                    # JSON မဟုတ်ဘဲ string ပြန်လာပါက handle လုပ်ရန်
                    print(f"API returned non-JSON response: {res.text}")
                    return None

                # Data structure အလိုက် ဈေးနှုန်းကို ရှာဖွေခြင်း
                if isinstance(data, dict):
                    price = data.get('markPrice') or data.get('lastPrice') or data.get('price')
                    return float(price) if price else None
                
                elif isinstance(data, list):
                    for item in data:
                        if item.get('symbol') == market_id or item.get('market') == market_id:
                            price = item.get('markPrice') or item.get('lastPrice') or item.get('price')
                            return float(price) if price else None
            else:
                print(f"API Error: Status {res.status_code} at {url}")
                return None
                
        except Exception as e:
            print(f"Price Fetch Error: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """Documentation ပါ Authenticated Order Placement logic"""
        timestamp = int(time.time() * 1000)
        
        # Pacifica မှ သတ်မှတ်ထားသော Payload format
        payload = {
            "agent": self.pub_key_str,
            "market": market_id,
            "side": side.upper(),
            "price": str(price),
            "size": str(size),
            "type": "LIMIT",
            "timestamp": timestamp
        }

        # JSON object ကို signature လုပ်ခြင်း
        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }

        try:
            res = requests.post(f"{self.base_url}/order", json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                result = res.json()
                print(f"Order Success: {side} at {price}")
                return result.get('order_id')
            else:
                print(f"Order Placement Failed: {res.text}")
                return None
        except Exception as e:
            print(f"Order Request Error: {e}")
            return None

    def check_order_status(self, order_id):
        """Order status စစ်ဆေးရန်"""
        try:
            url = f"{self.base_url}/order/{order_id}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json().get('status')
            return "UNKNOWN"
        except:
            return "UNKNOWN"
