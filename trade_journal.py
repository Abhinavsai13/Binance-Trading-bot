import csv
from datetime import datetime
import os

CSV_HEADER = [
    'trade_id', 'symbol', 'side', 'entry_price', 'exit_price',
    'quantity', 'leverage', 'entry_time', 'exit_time', 'profit_pct', 'status'
]

def log_trade_to_csv(trade_data):
    file_exists = os.path.isfile('trade_journal.csv')
    
    with open('trade_journal.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADER)
        writer.writerow(trade_data)

def update_trade_in_csv(trade_id, exit_price, profit_pct):
    updated_rows = []
    with open('trade_journal.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['trade_id'] == str(trade_id):
                row['exit_price'] = exit_price
                row['exit_time'] = datetime.now().isoformat()
                row['profit_pct'] = profit_pct
                row['status'] = 'CLOSED'
            updated_rows.append(row)
    
    with open('trade_journal.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(updated_rows)