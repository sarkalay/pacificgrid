import time
import json
import logging
from pacifica_client import PacificaClient

# Bot ၏ အခြေအနေကို သိရှိနိုင်ရန် Logging သတ်မှတ်ခြင်း
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FutureGridBot:
    def __init__(self):
        self.client = PacificaClient()
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.active_orders = {}

    def calculate_size_per_grid(self, curr_price):
        """Total Investment ပေါ်မူတည်၍ Grid တစ်ခုချင်းစီ၏ Size ကို တွက်ချက်ခြင်း"""
        setts = self.config['grid_settings']
        num_grids = setts['num_grids']
        total_usd = setts['total_investment_usd']
        leverage = self.config['leverage']

        # တစ်ထပ်ချင်းစီအတွက် အသုံးပြုမည့် USD (Margin)
        usd_per_grid = total_usd / num_grids
        
        # Market Price နှင့် နှိုင်းယှဉ်၍ ဝယ်ယူမည့် Coin ပမာဏကို တွက်ချက်ခြင်း
        # Leverage ကိုပါ ထည့်သွင်းစဉ်းစားပါသည်
        size = (usd_per_grid / curr_price) * leverage
        
        # MON ကဲ့သို့ coin များအတွက် decimal ချိန်ညှိရန် (ဥပမာ- အနည်းဆုံး 1 unit)
        return round(size, 2)

    def start(self):
        m_id = self.config['market_id']
        logging.info(f"--- {m_id} Grid Bot စတင်နေပါပြီ ---")
        
        # ၁။ လက်ရှိဈေးနှုန်းကို ရယူခြင်း
        curr_price = self.client.get_market_price(m_id)
        if curr_price is None:
            logging.error("ဈေးနှုန်းဆွဲယူ၍ မရပါ။ config.json ရှိ market_id ကို ပြန်စစ်ပါ။")
            return

        logging.info(f"လက်ရှိ {m_id} ဈေးနှုန်း: {curr_price}")
        
        setts = self.config['grid_settings']
        interval = (setts['upper_price'] - setts['lower_price']) / setts['num_grids']
        
        # ၂။ Grid တစ်ခုချင်းစီတွင် သုံးမည့် Size ကို တွက်ချက်ခြင်း
        size_per_grid = self.calculate_size_per_grid(curr_price)
        logging.info(f"စုစုပေါင်းရင်းနှီးမြှုပ်နှံမှု: ${setts['total_investment_usd']}")
        logging.info(f"Grid တစ်ခုစီ၏ ပမာဏ (Size): {size_per_grid} {m_id}")

        # ၃။ Initial Grid Orders များ ခင်းကျင်းခြင်း
        for i in range(setts['num_grids'] + 1):
            p = round(setts['lower_price'] + (i * interval), 5)
            # Neutral Strategy: ဈေးအထက်တွင် SHORT၊ အောက်တွင် LONG
            side = "SHORT" if p > curr_price else "LONG"
            
            # လက်ရှိဈေးနှင့် အရမ်းနီးကပ်သော grid ကို ကျော်ရန်
            if abs(p - curr_price) < (interval / 2): continue
            
            oid = self.client.place_order(side, p, size_per_grid, m_id)
            if oid:
                self.active_orders[oid] = {"side": side, "price": p, "size": size_per_grid}
                logging.info(f"တင်ပြီးသောအော်ဒါ: {side} at {p}")
            time.sleep(0.5) # API Rate Limit မမိစေရန်

        logging.info("Grid ခင်းကျင်းမှု ပြီးပါပြီ။ စောင့်ကြည့်နေပါသည်...")

        # ၄။ Monitoring and Rebalancing Loop
        while True:
            try:
                for oid, info in list(self.active_orders.items()):
                    status = self.client.check_order_status(oid)
                    
                    if status == "FILLED":
                        logging.info(f"အော်ဒါ ထိသွားပါပြီ: {info['side']} at {info['price']}")
                        
                        # Rebalance: Filled ဖြစ်သွားသောဘက်နှင့် ဆန့်ကျင်ဘက် အော်ဒါပြန်တင်ခြင်း
                        new_side = "SHORT" if info['side'] == "LONG" else "LONG"
                        new_p = round(info['price'] + interval if info['side'] == "LONG" else info['price'] - interval, 5)
                        
                        # သတ်မှတ်ထားသော Range အတွင်းမှာ ရှိနေမှသာ အော်ဒါအသစ်တင်မည်
                        if setts['lower_price'] <= new_p <= setts['upper_price']:
                            new_id = self.client.place_order(new_side, new_p, info['size'], m_id)
                            if new_id:
                                self.active_orders[new_id] = {"side": new_side, "price": new_p, "size": info['size']}
                        
                        del self.active_orders[oid]
                
                time.sleep(10) # ၁၀ စက္ကန့်ခြား တစ်ခါ Status စစ်ဆေးခြင်း
            except Exception as e:
                logging.error(f"Loop Error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    bot = FutureGridBot()
    bot.start()
