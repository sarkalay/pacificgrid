# deepseek_h1_5m_server.py
from flask import Flask, request, jsonify
import requests
import json
import re
import threading
import time

app = Flask(__name__)

# === CONFIG ===
DEEPSEEK_API_KEY = "sk-your-deepseek-key-here"  # ← ဒီနေရာမှာ ထည့်ပါ
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# === PROMPTS ===
PROMPT_ENTRY = """
1H CANDLE JUST CLOSED. DECIDE ENTRY ONLY.

Current Price: ${price}
RSI(14): {rsi} → {rsi_level}
EMA9: {ema9}, EMA21: {ema21} → Trend: {trend}
ATR: {atr}
Balance: ${balance}

DECIDE: LONG, SHORT, or HOLD
If trade: size $20-60, SL 8-20 points, TP 25-60 points

Return JSON ONLY:
{
  "decision": "LONG"|"SHORT"|"HOLD",
  "size_usd": number,
  "stop_loss": number,
  "take_profit": number,
  "reasoning": "short text"
}
"""

PROMPT_MANAGE = """
POSITION OPEN. Current Profit: ${profit} USD

Price: ${price}
RSI: {rsi}, EMA9: {ema9}, EMA21: {ema21}

DECIDE:
- CLOSE (if profit > 2% or loss > 1.5%)
- TRAIL (points to trail)
- REVERSE_LONG / REVERSE_SHORT
- MOVE_SL (new SL price)
- HOLD

Return JSON ONLY:
{
  "decision": "CLOSE"|"TRAIL"|"REVERSE_LONG"|"REVERSE_SHORT"|"MOVE_SL"|"HOLD",
  "trail_points": number,
  "stop_loss": number,
  "reasoning": "short text"
}
"""

def call_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 400
    }
    try:
        resp = requests.post(DEEPSEEK_URL, json=data, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            print(f"DeepSeek Error: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def extract_json(text):
    if not text: return {"decision": "HOLD"}
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {"decision": "HOLD"}

@app.route('/ai-decision', methods=['POST'])
def ai_decision():
    data = request.get_json()
    mode = data.get("mode", "ENTRY_CHECK")
    
    # Add derived fields
    rsi = float(data.get("indicators", {}).get("rsi", 50))
    data["rsi_level"] = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
    data["trend"] = "up" if data["indicators"]["ema9"] > data["indicators"]["ema21"] else "down"
    
    if mode == "ENTRY_CHECK":
        prompt = PROMPT_ENTRY.format(**data)
    else:
        profit = data.get("position_profit", 0)
        data["profit"] = round(profit, 2)
        prompt = PROMPT_MANAGE.format(**data)
    
    raw = call_deepseek(prompt)
    result = extract_json(raw)
    result["reasoning"] = result.get("reasoning", "AI decision")
    return jsonify(result)

# Keep server alive
def keep_alive():
    while True:
        time.sleep(3600)
        print("Server alive...")

if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    print("DeepSeek H1+5M AI Server Running on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
