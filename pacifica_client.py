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
        # Base URL ကို documentation အတိုင်း ပြန်စစ်ဆေးထားသည်
        self.base_url = "https://api.pacifica.fi/v1" 

    def get_market_price(self, market_id):
        """လက်ရှိဈေးနှုန်းကို ဆွဲယူရန် (Error message အသေးစိတ်ပြမည်)"""
        try:
            # တချို့ API တွေက MON လို့ပဲလိုသလို တချို့က MON-USD လိုပါတယ်
            url = f"{self.base_url}/ticker?market={market_id}"
            res = requests.get(url)
            
            if res.status_code == 200:
                data = res.json()
                # Pacifica API ရဲ့ JSON structure အရ 'lastPrice' သို့မဟုတ် 'markPrice' ဖြစ်နိုင်သည်
                return float(data.get('lastPrice') or data.get('markPrice') or data.get('price'))
            else:
                print(f"API Error: Status {res.status_code} - {res.text}")
                return None
        except Exception as e:
            print(f"Connection Error: {e}")
            return None

    def place_order(self, side, price, size):
        """Order တင်ခြင်း"""
        timestamp = int(time.time() * 1000)
        payload = {
            "agent": self.pub_key_str,
            "side": side,
            "price": str(price),
            "size": str(size),
            "timestamp": timestamp,
            "market": os.getenv("MARKET_ID", "MON-USD") # Market ID ထည့်ရန် လိုအပ်နိုင်သည်
        }
        
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
            print(f"Order Placement Error: {res.text}")
            return None

    def check_order_status(self, order_id):
        try:
            res = requests.get(f"{self.base_url}/order/{order_id}")
            return res.json().get('status')
        except: return "UNKNOWN"
