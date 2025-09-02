#!/usr/bin/env python3
# fetch_p2p.py
# Consulta precios P2P (Binance) y guarda/actualiza data/data/p2p_bob_usdt.csv

import requests
import pandas as pd
import os
import time
import statistics
from datetime import datetime, timezone

P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

DATA_PATH = "data/p2p_bob_usdt.csv"
ASSET = "USDT"
FIAT = "BOB"
ROWS = 20

def fetch_prices(asset=ASSET, fiat=FIAT, trade_type="BUY", rows=ROWS):
    payload = {
        "asset": asset,
        "fiat": fiat,
        "tradeType": trade_type,
        "page": 1,
        "rows": rows,
        "merchantCheck": False
    }
    for attempt in range(4):
        try:
            r = requests.post(P2P_URL, json=payload, headers=HEADERS, timeout=15)
            r.raise_for_status()
            j = r.json()
            data = j.get("data", [])
            prices = []
            for item in data:
                price_str = item.get("adv", {}).get("price")
                if price_str:
                    price_str = price_str.replace(",", "")
                    try:
                        prices.append(float(price_str))
                    except:
                        pass
            return prices
        except Exception as e:
            wait = 1.5 ** attempt
            print(f"[fetch_prices] intento {attempt+1} falló: {e}. Reintentando en {wait:.1f}s")
            time.sleep(wait)
    return []

def median_or_none(lst):
    return statistics.median(lst) if lst else None

def build_row():
    now = datetime.now(timezone.utc).isoformat()
    buy = fetch_prices(trade_type="BUY")
    sell = fetch_prices(trade_type="SELL")

    buy_median = median_or_none(buy)
    sell_median = median_or_none(sell)

    market_median = None
    if buy_median is not None and sell_median is not None:
        market_median = (buy_median + sell_median) / 2.0
    elif buy_median is not None:
        market_median = buy_median
    elif sell_median is not None:
        market_median = sell_median

    row = {
        "datetime_utc": now,
        "asset": ASSET,
        "fiat": FIAT,
        "buy_count": len(buy),
        "buy_median": buy_median,
        "buy_avg": (sum(buy)/len(buy)) if buy else None,
        "buy_min": min(buy) if buy else None,
        "buy_max": max(buy) if buy else None,
        "sell_count": len(sell),
        "sell_median": sell_median,
        "sell_avg": (sum(sell)/len(sell)) if sell else None,
        "sell_min": min(sell) if sell else None,
        "sell_max": max(sell) if sell else None,
        "market_median": market_median
    }
    return row

def append_csv(path, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_new = pd.DataFrame([row])
    if os.path.exists(path):
        df_old = pd.read_csv(path)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(path, index=False)
    return df

def main():
    row = build_row()
    df = append_csv(DATA_PATH, row)
    print("Fila añadida correctamente. Última fila:")
    print(df.tail(1).to_dict(orient="records")[0])

if __name__ == "__main__":
    main()
