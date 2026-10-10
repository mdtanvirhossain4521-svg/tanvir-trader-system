import time
import requests
import pandas as pd
import ta
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Tanvir Trader 99 Zone Cloud Backend")

CORRECT_PASSWORD = "2T1A1N2V7I0R"
API_KEY = "2a7e959ba337459b8a9f4fa27e6b53fb" # এখানে আপনার TwelveData এপিআই কি বসাবেন
DEFAULT_PAIR = "EUR/USD"

@app.get("/")
def home():
    return {"status": "Online", "system": "Tanvir Trader 99 Zone 24/7 Active"}

@app.get("/check_signal")
def check_signal(password: str, symbol: str = DEFAULT_PAIR):
    if password != CORRECT_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid Password")
    
    formatted_symbol = symbol.upper().strip()
    if "/" not in formatted_symbol and len(formatted_symbol) == 6:
        formatted_symbol = f"{formatted_symbol[:3]}/{formatted_symbol[3:]}"

    url = f"https://api.twelvedata.com/time_series?symbol={formatted_symbol}&interval=1min&outputsize=100&apikey={API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "values" not in data:
            return {"pair": formatted_symbol, "signal": "WAIT", "reason": "Market data loading..."}

        df = pd.DataFrame(data['values'])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df = df.iloc[::-1].reset_index(drop=True)

        # ইন্ডিকেটর ক্যালকুলেশন (EMA 200 + RSI 14 + ATR 14)
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)

        curr = df.iloc[-1]
        close_p, open_p = curr['close'], curr['open']
        ema, rsi, atr = curr['ema200'], curr['rsi'], curr['atr']

        if pd.isna(ema) or atr < 0.0001:
            return {"pair": formatted_symbol, "signal": "WAIT", "reason": "Flat market"}

        if close_p > ema and 48 < rsi < 65 and close_p > open_p:
            return {
                "pair": formatted_symbol,
                "signal": "BUY",
                "reason": f"Uptrend | RSI: {round(rsi, 1)}",
                "speech": f"সম্মানিত ট্রেডার, {formatted_symbol.replace('/', ' ')} মার্কেটে একটি সঠিক বাই সেটআপ তৈরি হয়েছে। এন্ট্রি নিন।"
            }
        elif close_p < ema and 35 < rsi < 52 and close_p < open_p:
            return {
                "pair": formatted_symbol,
                "signal": "SELL",
                "reason": f"Downtrend | RSI: {round(rsi, 1)}",
                "speech": f"সম্মানিত ট্রেডার, {formatted_symbol.replace('/', ' ')} মার্কেটে একটি সঠিক সেল সেটআপ তৈরি হয়েছে। এন্ট্রি নিন।"
            }

        return {"pair": formatted_symbol, "signal": "WAIT", "reason": "No setup"}
    except Exception as e:
        return {"pair": formatted_symbol, "signal": "ERROR", "reason": str(e)}
