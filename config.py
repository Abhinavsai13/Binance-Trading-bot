# Strategy Parameters
STRATEGY_CONFIG = {
    "timeframe": "1m",           # 1m, 5m, 15s (Binance futures supported timeframes)
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],  # Futures symbols
    "leverage": 25,              # Leverage (1-125)
    
    # Entry/Exit Rules
    "profit_target": 0.2,        # 0.2% profit per trade (pre-leverage)
    "stop_loss": 0.15,           # 0.15% stop-loss (pre-leverage)
    "min_model_confidence": 0.75, # 75% prediction probability threshold
    
    # Risk Management
    "max_daily_trades": 20,
    "risk_per_trade": 1,         # 1% of account per trade
    
    # Model Settings
    "features": ["rsi", "macd", "order_book_imbalance", "volume_zscore"],
    "retrain_interval": 3600     # Retrain model every 1 hour (in seconds)
}