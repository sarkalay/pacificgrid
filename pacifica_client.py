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
        # SDK အရ base url သည် https://api.pacifica.fi/v1 ဖြစ်သည်
        self.base_url = "https://api.pacifica.fi/v1" 

    def get_market_price(self, market_id):
        """SDK စံနှုန်းအတိုင်း ဈေးနှုန်းယူခြင်း"""
        try:
            # SDK ထဲတွင် ticker endpoint သုံး၍ ဈေးနှုန်းယူသည်
            url = f"{self.base_url}/ticker?market={market_id}"
            res = requests.get(url, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                # SDK data structure အရ price ကို ဆွဲထုတ်ခြင်း
                price = data.get('lastPrice') or data.get('price') or data.get('markPrice')
                return float(price) if price else None
            else:
                print(f"Price Fetch Error: {res.status_code}")
                return None
        except Exception as e:
            print(f"Price Fetch Exception: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """SDK ပါ create_limit_order logic အတိုင်း အော်ဒါတင်ခြင်း"""
        timestamp = int(time.time() * 1000)
        
        # SDK payload format အတိအကျ
        payload = {
            "agent": self.pub_key_str,
            "market": market_id,
            "side": side.upper(),
            "price": str(price), # SDK အရ string ပြောင်းရမည်
            "size": str(size),   # SDK အရ string ပြောင်းရမည်
            "type": "LIMIT",     # Limit order ဖြစ်သည်
            "timestamp": timestamp
        }

        # SDK နည်းလမ်းအတိုင်း Signature ပြုလုပ်ခြင်း
        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }

        try:
            # SDK ကဲ့သို့ /order endpoint သို့ POST ပို့ခြင်း
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
