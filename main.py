import time
import json
from pacifica_client import PacificaClient

class FutureGridBot:
    def __init__(self):
        self.client = PacificaClient()
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.active_orders = {}

    def start(self):
        print("Bot စတင်နေပါပြီ...")
        curr_price = self.client.get_market_price(self.config['market_id'])
        setts = self.config['grid_settings']
        interval = (setts['upper_price'] - setts['lower_price']) / setts['num_grids']

        # Initial Grid Orders ချခြင်း
        for i in range(setts['num_grids'] + 1):
            p = round(setts['lower_price'] + (i * interval), 2)
            side = "SHORT" if p > curr_price else "LONG"
            if abs(p - curr_price) < (interval / 2): continue
            
            oid = self.client.place_order(side, p, setts['size_per_grid'])
            if oid: self.active_orders[oid] = {"side": side, "price": p}
            time.sleep(0.5)

        # Monitoring Loop
        while True:
            for oid, info in list(self.active_orders.items()):
                if self.client.check_order_status(oid) == "FILLED":
                    print(f"Order ထိသွားပါပြီ: {info['side']} at {info['price']}")
                    # Rebalance Logic
                    new_side = "SHORT" if info['side'] == "LONG" else "LONG"
                    new_p = info['price'] + interval if info['side'] == "LONG" else info['price'] - interval
                    new_id = self.client.place_order(new_side, new_p, setts['size_per_grid'])
                    if new_id: self.active_orders[new_id] = {"side": new_side, "price": new_p}
                    del self.active_orders[oid]
            time.sleep(10)

if __name__ == "__main__":
    bot = FutureGridBot()
    bot.start()
