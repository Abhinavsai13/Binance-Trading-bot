from binance import Client
import pandas as pd
import time

# No need for an API key
client = Client()

# Function to fetch historical data in batches
def get_full_binance_data(symbol="BTCUSDT", interval="5m", days=30):
    df_list = []
    last_timestamp = None
    limit = 1000  # Binance max per request

    # Mapping intervals to minutes
    interval_map = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    if interval not in interval_map:
        raise ValueError("Unsupported interval. Choose from: 1m, 5m, 15m, 30m, 1h, 4h, 1d")
    
    # Calculate total candles needed
    candles_per_day = 24 * 60 / interval_map[interval]  # Converts interval to minutes
    total_candles = int(days * candles_per_day)

    while total_candles > 0:
        fetch_limit = min(limit, total_candles)  # Ensure we don’t fetch more than needed
        print(f"Fetching {fetch_limit} candles... Remaining: {total_candles}")

        # Fetch historical data
        if last_timestamp:
            klines = client.get_klines(symbol=symbol, interval=interval, limit=fetch_limit, endTime=last_timestamp)
        else:
            klines = client.get_klines(symbol=symbol, interval=interval, limit=fetch_limit)

        if not klines:
            print("No more data available.")
            break

        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume", "_", "_", "_", "_", "_", "_"
        ])
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)

        df_list.append(df)

        # Update last timestamp to continue fetching older data
        last_timestamp = int(df.index[0].timestamp() * 1000)
        total_candles -= fetch_limit

        # Binance API rate limit (avoid getting banned)
        time.sleep(0.5)

    full_df = pd.concat(df_list).sort_index()
    return full_df

# Fetch last 30 days of 1-hour BTC/USDT data
df = get_full_binance_data(symbol="BTCUSDT", interval="1h", days=30)
df.to_csv("crypto_data.csv")

print(df.head())
print(f"Total data points collected: {len(df)}")
