import os
import time
import json
import requests
from solders.keypair import Keypair
from dotenv import load_dotenv

# .env ဖိုင်မှ Key များကို Load လုပ်ခြင်း
load_dotenv()

class PacificaClient:
    def __init__(self):
        # Private Key ကို Base58 မှ Keypair အဖြစ်ပြောင်းခြင်း
        self.priv_key = os.getenv("PACIFICA_AGENT_PRIVATE_KEY")
        if not self.priv_key:
            raise ValueError(".env ဖိုင်ထဲတွင် PACIFICA_AGENT_PRIVATE_KEY မရှိပါ။")
        
        self.agent_kp = Keypair.from_base58_string(self.priv_key.strip())
        self.pub_key_str = os.getenv("PACIFICA_AGENT_PUBLIC_KEY")
        
        # Pacifica API Base URL
        # မှတ်ချက် - v1 သို့မဟုတ် api/v1 ဖြစ်နိုင်၍ ဈေးနှုန်းမရပါက ဤနေရာတွင် ပြင်ဆင်ပါ
        self.base_url = "https://api.pacifica.fi/api/v1" 

    def get_market_price(self, market_id):
        """Pacifica API မှ Mark Price သို့မဟုတ် Last Price ကို ရယူခြင်း"""
        try:
            # /info/prices endpoint သည် symbol အားလုံး၏ ဈေးနှုန်းကို ပြန်ပေးသည်
            url = f"{self.base_url}/info/prices"
            res = requests.get(url, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                
                # အကယ်၍ data သည် list အနေဖြင့် ပြန်လာပါက
                if isinstance(data, list):
                    for item in data:
                        # 'MON' သို့မဟုတ် 'MON-USD' ဖြစ်နိုင်၍ နှစ်မျိုးလုံးစစ်သည်
                        if item.get('symbol') == market_id or item.get('market') == market_id:
                            # mark price ကို ဦးစားပေးယူသည်
                            price = item.get('mark') or item.get('last') or item.get('price')
                            return float(price)
                
                # အကယ်၍ data သည် dictionary အနေဖြင့် ပြန်လာပါက
                elif isinstance(data, dict):
                    # nested data ရှိမရှိ စစ်ဆေးခြင်း
                    market_data = data.get(market_id) or data.get('data', {}).get(market_id)
                    if market_data:
                        price = market_data.get('mark') or market_data.get('last') or market_data.get('price')
                        return float(price)

                print(f"Error: Market '{market_id}' ကို List ထဲတွင် ရှာမတွေ့ပါ။")
                return None
            else:
                # URL မှားနေပါက ဤနေရာတွင် သိနိုင်သည်
                print(f"API Error: Status {res.status_code} at {url}")
                return None
                
        except Exception as e:
            print(f"Price Fetch Connection Error: {e}")
            return None

    def place_order(self, side, price, size, market_id):
        """အော်ဒါတင်ခြင်းနှင့် Signature ထည့်သွင်းခြင်း logic"""
        timestamp = int(time.time() * 1000)
        
        # Pacifica SDK တောင်းဆိုသော Payload format
        payload = {
            "agent": self.pub_key_str,
            "market": market_id,
            "side": side.upper(),
            "price": str(price),
            "size": str(size),
            "type": "LIMIT",
            "timestamp": timestamp
        }

        # JSON format ကို Sign လုပ်ခြင်း
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
                order_id = res.json().get('order_id')
                print(f"Successfully placed {side} at {price}. ID: {order_id}")
                return order_id
            else:
                print(f"Order Placement Failed: {res.text}")
                return None
        except Exception as e:
            print(f"Order Connection Error: {e}")
            return None

    def check_order_status(self, order_id):
        """အော်ဒါ အခြေအနေ စစ်ဆေးခြင်း"""
        try:
            url = f"{self.base_url}/order/{order_id}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json().get('status')
            return "UNKNOWN"
        except:
            return "UNKNOWN"
