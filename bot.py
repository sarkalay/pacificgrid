from flask import Flask, request, jsonify
import requests
import json
import re
import threading
import time

app = Flask(__name__)

# === CONFIG ===
DEEPSEEK_API_KEY = "sk-your-key-here"  # ← ဒီနေရာမှာ သင့် key ထည့်ပါ
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# === ANYTIME ENTRY PROMPT ===
PROMPT_ENTRY = """
ANYTIME ENTRY ALLOWED - Analyze Multi-Timeframe

Current Price: ${price}
Balance: ${balance}
Open Positions: {positions}

=== H1 Indicators ===
RSI(14): {rsi} → {rsi_level}
EMA9: {ema9}, EMA21: {ema21} → Trend: {trend}
ATR: {atr}

You can enter LONG or SHORT at ANY TIME if signal is strong.
Only HOLD if no clear signal.

Return JSON ONLY:
{
  "decision": "LONG"|"SHORT"|"HOLD",
  "size_usd": 20|30|40|50|60,
  "stop_loss": 8|10|12|15|18|20,
  "take_profit": 25|30|40|50|60,
  "reasoning": "short reason"
}
"""

PROMPT_MANAGE = """
POSITION OPEN. Profit: ${profit} USD

Price: ${price}
RSI: {rsi}, EMA9: {ema9}, EMA21: {ema21}

DECIDE:
- CLOSE (if profit > 2% or loss > 1.5%)
- TRAIL (points)
- REVERSE_LONG / REVERSE_SHORT
- MOVE_SL (new points)
- HOLD

Return JSON:
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
    
    indicators = data.get("indicators", {})
    rsi = float(indicators.get("rsi", 50))
    data["rsi_level"] = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
    data["trend"] = "up" if indicators.get("ema9", 0) > indicators.get("ema21", 0) else "down"
    
    if mode == "ENTRY_CHECK":
        prompt = PROMPT_ENTRY.format(**data)
    else:
        data["profit"] = round(data.get("position_profit", 0), 2)
        prompt = PROMPT_MANAGE.format(**data)
    
    raw = call_deepseek(prompt)
    result = extract_json(raw)
    result["reasoning"] = result.get("reasoning", "AI decision")
    return jsonify(result)

def keep_alive():
    while True:
        time.sleep(3600)
        print("Server alive...")

if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    print("XAU AI Anytime Server → http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
