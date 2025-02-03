import ccxt
import pandas as pd
import xgboost as xgb
import time
import sqlite3
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from config import STRATEGY_CONFIG
from database import initialize_database, log_trade, update_trade, get_open_trades
from trade_journal import log_trade_to_csv, update_trade_in_csv
from indicators import compute_rsi, compute_macd

# Initialize Exchange Connection
binance = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

# Set Leverage for All Symbols
for symbol in STRATEGY_CONFIG["symbols"]:
    try:
        binance.futures_change_leverage(symbol=symbol, leverage=STRATEGY_CONFIG["leverage"])
    except Exception as e:
        print(f"Error setting leverage for {symbol}: {e}")

# Initialize Database
initialize_database()

def fetch_ohlcv(symbol):
    """Fetch OHLCV data from Binance"""
    return binance.fetch_ohlcv(
        symbol, 
        STRATEGY_CONFIG["timeframe"], 
        limit=1000
    )

def calculate_features(df, symbol):
    """Calculate technical features"""
    df['rsi'] = compute_rsi(df['close'], 14)
    df['macd'], df['signal'] = compute_macd(df['close'])
    
    # Order Book Imbalance (real-time)
    order_book = binance.fetch_order_book(symbol)
    bid = sum([b[1] for b in order_book['bids'][:5]])
    ask = sum([a[1] for a in order_book['asks'][:5]])
    df['order_book_imbalance'] = (bid - ask) / (bid + ask) if (bid + ask) != 0 else 0
    
    return df.dropna()

class ScalpingModel:
    def __init__(self):
        self.model = xgb.XGBClassifier()
        self.scaler = StandardScaler()
        self.last_trained = time.time()

    def train(self, X, y):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)[:, 1]

def execute_strategy(symbol, model):
    """Execute trading logic for one symbol"""
    try:
        # Fetch and prepare data
        ohlcv = fetch_ohlcv(symbol)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = calculate_features(df, symbol)
        
        # Generate prediction
        features = df[STRATEGY_CONFIG["features"]].tail(1)
        proba = model.predict(features)[0]
        
        # Get current price
        ticker = binance.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Trade execution logic
        if proba >= STRATEGY_CONFIG["min_model_confidence"]:
            account_info = binance.futures_account()
            balance = float([a for a in account_info['assets'] if a['asset'] == 'USDT'][0]['marginBalance'])
            
            # Calculate position size
            risk_amount = balance * (STRATEGY_CONFIG["risk_per_trade"] / 100)
            stop_loss_pct = STRATEGY_CONFIG["stop_loss"] / 100
            position_size = risk_amount / (current_price * stop_loss_pct)
            
            # Place order
            order = binance.create_market_buy_order(
                symbol=symbol,
                amount=position_size
            )
            
            # Log trade
            trade_id = log_trade(
                symbol=symbol,
                side='LONG',
                entry_price=current_price,
                quantity=position_size,
                leverage=STRATEGY_CONFIG["leverage"]
            )
            
            log_trade_to_csv([
                trade_id, symbol, 'LONG', current_price, None,
                position_size, STRATEGY_CONFIG["leverage"],
                datetime.now().isoformat(), None, None, 'OPEN'
            ])
            
            # Place OCO order
            tp_price = round(current_price * (1 + STRATEGY_CONFIG["profit_target"]/100), 4)
            sl_price = round(current_price * (1 - STRATEGY_CONFIG["stop_loss"]/100), 4)
            
            binance.create_order(
                symbol=symbol,
                type='TAKE_PROFIT_MARKET',
                side='SELL',
                stopPrice=tp_price,
                closePosition=True
            )
            
            binance.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side='SELL',
                stopPrice=sl_price,
                closePosition=True
            )

    except Exception as e:
        print(f"Error executing strategy for {symbol}: {e}")

def monitor_open_trades():
    """Check and update open positions"""
    open_trades = get_open_trades()
    for trade in open_trades:
        trade_id, symbol, side, entry_price, exit_price, quantity, leverage, entry_time, exit_time, profit_pct, status = trade
        
        try:
            ticker = binance.fetch_ticker(symbol)
            current_price = ticker['last']
            
            if side == 'LONG':
                profit = (current_price - entry_price) / entry_price * 100
                
                # Check exit conditions
                if profit >= STRATEGY_CONFIG["profit_target"] or \
                   profit <= -STRATEGY_CONFIG["stop_loss"]:
                    
                    # Update database
                    update_trade(trade_id, current_price, profit)
                    
                    # Update CSV journal
                    update_trade_in_csv(trade_id, current_price, profit)
                    
                    print(f"Closed {symbol} trade {trade_id} with {profit:.2f}% PNL")

        except Exception as e:
            print(f"Error monitoring trade {trade_id}: {e}")

if __name__ == "__main__":
    # Initialize models for each symbol
    models = {symbol: ScalpingModel() for symbol in STRATEGY_CONFIG["symbols"]}
    
    # Initial training
    for symbol, model in models.items():
        ohlcv = fetch_ohlcv(symbol)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = calculate_features(df, symbol)
        X = df[STRATEGY_CONFIG["features"]]
        y = (df['close'].shift(-5) > df['close'] * (1 + STRATEGY_CONFIG["profit_target"]/100)).astype(int)
        model.train(X[:-5], y[:-5])  # Avoid lookahead bias
    
    # Main trading loop
    while True:
        try:
            # Monitor existing trades first
            monitor_open_trades()
            
            # Execute new trades
            for symbol, model in models.items():
                execute_strategy(symbol, model)
                
                # Retrain model periodically
                if time.time() - model.last_trained > STRATEGY_CONFIG["retrain_interval"]:
                    ohlcv = fetch_ohlcv(symbol)
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df = calculate_features(df, symbol)
                    X = df[STRATEGY_CONFIG["features"]]
                    y = (df['close'].shift(-5) > df['close'] * (1 + STRATEGY_CONFIG["profit_target"]/100)).astype(int)
                    model.train(X[:-5], y[:-5])
                    model.last_trained = time.time()
                    print(f"Retrained model for {symbol}")
                
                time.sleep(1/len(STRATEGY_CONFIG["symbols"]))  # Rate limit handling
            
        except Exception as e:
            print(f"Critical error in main loop: {e}")
            time.sleep(60)