import json
import subprocess
import time
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from rich import print
from rich.live import Live
from rich.table import Table
from rich.console import Console
from bs4 import BeautifulSoup
import random
import yfinance as yf

def get_stock_data(symbol):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    url = f'https://finance.yahoo.com/quote/{symbol.upper()}'
    print(f"\n[yellow]Fetching data from: {url}[/yellow]")
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        price_element = soup.find('fin-streamer', {
            'class': 'livePrice',
            'data-symbol': symbol.upper(),
            'data-field': 'regularMarketPrice'
        })
        
        if price_element:
            price_str = price_element.get('data-value', '').strip()
            if price_str and price_str != '-':
                current_price = float(price_str)
                print(f"[green]Found price: ${current_price}[/green]")
                return current_price
        
        print(f"[red]Could not find valid price data for {symbol}[/red]")
        return None
            
    except Exception as e:
        print(f"[red]Error scraping data: {str(e)}[/red]")
        return None

def create_price_table(symbol, current_price, target_price, prices_history):
    table = Table(title=f"{symbol} Price Tracking")
    table.add_column("Time")
    table.add_column("Price")
    table.add_column("Target")
    table.add_column("Diff %")
    
    for timestamp, price in prices_history[-10:]:
        diff_pct = ((price - target_price) / target_price) * 100
        color = "green" if price >= target_price else "red"
        table.add_row(
            timestamp.strftime("%H:%M:%S"),
            f"${price:.2f}",
            f"${target_price:.2f}",
            f"[{color}]{diff_pct:.2f}%[/{color}]"
        )
    return table

def track_stock(symbol, target_price, date):
    console = Console()
    prices_history = []
    
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            try:
                current_price = get_stock_data(symbol)
                if current_price is not None:
                    prices_history.append((datetime.now(), current_price))
                    
                    if len(prices_history) > 60:
                        prices_history.pop(0)
                    
                    table = create_price_table(symbol, current_price, target_price, prices_history)
                    live.update(table)
                
                # Random delay between 10-15 seconds
                delay = random.uniform(10, 15)
                time.sleep(delay)
                
            except KeyboardInterrupt:
                print("\nStopping price tracking...")
                break
            except Exception as e:
                print(f"[red]Error: {e}[/red]")
                # Longer delay on error (30-60 seconds)
                time.sleep(random.uniform(30, 60))

def search_stock_symbol(query):
    """Search for stock symbol using Yahoo Finance Autocomplete API."""
    try:
        url = 'https://query2.finance.yahoo.com/v1/finance/search'
        params = {'q': query, 'quotes_count': 1, 'news_count': 0}
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if 'quotes' in data and len(data['quotes']) > 0:
            symbol = data['quotes'][0]['symbol']
            print(f"[green]Found symbol {symbol} for '{query}'[/green]")
            return symbol.upper()
        else:
            print(f"[yellow]No symbol found for '{query}'[/yellow]")
            return None
            
    except Exception as e:
        print(f"[red]Error searching symbol: {str(e)}[/red]")
        return None

def format_date(date_str):
    """Convert date string to YYYY-MM-DD format."""
    date_str = date_str.lower()
    if date_str in ['eod', 'end of day', 'today']:
        return datetime.now().strftime('%Y-%m-%d')
    elif date_str == 'tomorrow':
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        # Try parsing common date formats
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        print(f"[yellow]Unrecognized date format: '{date_str}'[/yellow]")
        return datetime.now().strftime('%Y-%m-%d')

def get_prediction(input_text):
    """
    Parse the user's prediction input and return a prediction dictionary.
    Expected format: "<company_name_or_symbol> <target_price> by <date>"
    Example: "nvidea 145 by eod"
    """
    try:
        tokens = input_text.strip().split()
        if len(tokens) < 2:
            print("[yellow]Input doesn't contain enough information.[/yellow]")
            return None

        # First token: company name or symbol
        query = tokens[0]
        symbol = search_stock_symbol(query)
        if not symbol:
            print(f"[yellow]Could not find valid stock symbol for '{query}'[/yellow]")
            return None

        # Extract target price
        target_price = None
        for token in tokens[1:]:
            try:
                target_price = float(token.replace('$', '').replace(',', ''))
                break
            except ValueError:
                continue

        if target_price is None:
            print("[yellow]Could not find target price in input.[/yellow]")
            return None

        # Extract date after "by"
        date = datetime.now().strftime('%Y-%m-%d')  # Default to today
        if 'by' in tokens:
            by_index = tokens.index('by')
            if by_index + 1 < len(tokens):
                date_str = ' '.join(tokens[by_index + 1:])
                date = format_date(date_str)
            else:
                print("[yellow]Date not specified after 'by'. Using default date.[/yellow]")
        else:
            print("[yellow]'by' keyword not found. Using default date.[/yellow]")

        prediction = {
            'symbol': symbol,
            'target_price': target_price,
            'date': date
        }
        print(f"[blue]Parsed prediction: {prediction}[/blue]")
        return prediction

    except Exception as e:
        print(f"[red]Error parsing prediction: {str(e)}[/red]")
        return None

def main():
    print("[green]Stock Price Prediction Tracker[/green]")
    print("Enter 'quit' to exit")
    
    while True:
        try:
            user_input = input("\nEnter your prediction: ")
            if user_input.lower() == 'quit':
                break
                
            prediction = get_prediction(user_input)
            if prediction:
                print(f"[blue]Processing prediction for {prediction['symbol']}[/blue]")
                
                with open('predictions.json', 'a') as f:
                    json.dump(prediction, f)
                    f.write('\n')
                    
                track_stock(
                    prediction['symbol'],
                    float(prediction['target_price']),
                    prediction.get('date', datetime.now().strftime('%Y-%m-%d'))
                )
                
        except KeyboardInterrupt:
            print("\nExiting program.")
            break
        except Exception as e:
            print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()