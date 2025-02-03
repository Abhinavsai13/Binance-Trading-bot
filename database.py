import sqlite3
from datetime import datetime

def initialize_database():
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    
    # Create trades table
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  symbol TEXT,
                  side TEXT,
                  entry_price REAL,
                  exit_price REAL,
                  quantity REAL,
                  leverage INTEGER,
                  entry_time DATETIME,
                  exit_time DATETIME,
                  profit_pct REAL,
                  status TEXT)''')  # status: OPEN/CLOSED
    
    conn.commit()
    conn.close()

def log_trade(symbol, side, entry_price, quantity, leverage):
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO trades 
                 (symbol, side, entry_price, quantity, leverage, entry_time, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (symbol, side, entry_price, quantity, leverage, datetime.now(), 'OPEN'))
    
    conn.commit()
    conn.close()

def update_trade(trade_id, exit_price, profit_pct):
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    
    c.execute('''UPDATE trades 
                 SET exit_price=?, exit_time=?, profit_pct=?, status=?
                 WHERE id=?''',
              (exit_price, datetime.now(), profit_pct, 'CLOSED', trade_id))
    
    conn.commit()
    conn.close()

def get_open_trades():
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM trades WHERE status='OPEN'")
    open_trades = c.fetchall()
    
    conn.close()
    return open_trades