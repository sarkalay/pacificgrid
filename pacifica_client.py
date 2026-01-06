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
        # SDK အရ API endpoint သည် /v1 အောက်တွင် ရှိသည်
        self.base_url = "https://api.pacifica.fi/v1" 

    def get_market_price(self, market_id):
        """SDK အတိုင်း Market Price ကို ဆွဲယူခြင်း"""
        try:
            # SDK ထဲတွင် ticker သို့မဟုတ် markets query သုံးလေ့ရှိသည်
            res = requests.get(f"{self.base_url}/ticker?market={market_id}")
            data = res.json()
            
            if res.status_code == 200:
                # Pacifica SDK အရ ဈေးနှုန်းကို 'last' သို့မဟုတ် 'markPrice' ဖြင့် ပြန်ပေးလေ့ရှိသည်
                return float(data.get('lastPrice') or data.get('price') or data.get('markPrice'))
            else:
                print(f"API Error: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            print(f"Price Connection Error: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """SDK ပါ အော်ဒါတင်ခြင်း logic"""
        timestamp = int(time.time() * 1000)
        
        # SDK ပါ Batch Order format အရ market id သည် မဖြစ်မနေ ပါရမည်
        payload = {
            "agent": self.pub_key_str,
            "market": market_id,
            "side": side.upper(),
            "price": str(price),
            "size": str(size),
            "type": "LIMIT",
            "timestamp": timestamp
        }

        # SDK နည်းလမ်းအတိုင်း JSON message ကို Sign လုပ်ခြင်း
        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }

        res = requests.post(f"{self.base_url}/order", json=payload, headers=headers)
        if res.status_code == 200:
            return res.json().get('order_id')
        else:
            print(f"Order Placement Failed: {res.text}")
            return None

    def check_order_status(self, order_id):
        """Order status စစ်ဆေးခြင်း"""
        try:
            res = requests.get(f"{self.base_url}/order/{order_id}")
            return res.json().get('status')
        except:
            return "UNKNOWN"
