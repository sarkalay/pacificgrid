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
        self.agent_kp = Keypair.from_base58_string(self.priv_key)
        self.pub_key_str = os.getenv("PACIFICA_AGENT_PUBLIC_KEY")
        self.base_url = "https://api.pacifica.fi/v1"

    def get_market_price(self, market_id):
        try:
            res = requests.get(f"{self.base_url}/ticker?market={market_id}")
            return float(res.json()['lastPrice'])
        except: return None

    def place_order(self, side, price, size):
        timestamp = int(time.time() * 1000)
        payload = {
            "agent": self.pub_key_str,
            "side": side,
            "price": str(price),
            "size": str(size),
            "timestamp": timestamp
        }
        # GitHub SDK ပါ logic အတိုင်း Sign လုပ်ခြင်း
        msg = json.dumps(payload, separators=(',', ':')).encode()
        sig = self.agent_kp.sign_message(msg)
        
        headers = {
            "X-Agent-Signature": str(sig),
            "X-Agent-Pubkey": self.pub_key_str,
            "Content-Type": "application/json"
        }
        res = requests.post(f"{self.base_url}/order", json=payload, headers=headers)
        return res.json().get('order_id')

    def check_order_status(self, order_id):
        res = requests.get(f"{self.base_url}/order/{order_id}")
        return res.json().get('status')
