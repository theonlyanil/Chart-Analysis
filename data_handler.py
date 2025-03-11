import yfinance as yf
import pandas as pd
import random
import streamlit as st
from constants import INTERVALS

def get_random_period(interval):
    """Gets random start and end dates based on interval."""
    current_date = pd.Timestamp.now()
    
    # First determine the random end date in the past
    if interval in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]:
        # Intraday data - limited to 7 days, end date within last 30 days
        days_back = random.randint(7, 30)
        end_date = current_date - pd.Timedelta(days=days_back)
        start_date = end_date - pd.Timedelta(days=7)
    elif interval in ["1d", "5d"]:
        # Daily data - end date randomly between 30-730 days ago
        days_back = random.randint(60, 1200)
        end_date = current_date - pd.Timedelta(days=days_back)
        start_date = end_date - pd.Timedelta(days=400)
    else:
        # Weekly/Monthly data - end date randomly between 90-730 days ago
        days_back = random.randint(90, 4000)
        end_date = current_date - pd.Timedelta(days=days_back)
        start_date = end_date - pd.Timedelta(days=1000)
    
    # Ensure end_date doesn't exceed current date
    end_date = min(end_date, current_date)
    
    # Format dates to string to avoid timezone issues
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')
    
    return start_date, end_date

def get_data(symbol, interval):
    """Fetches data from yfinance with random period."""
    try:
        start_date, end_date = get_random_period(interval)
        
        # Create Ticker object and get data
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if data.empty:
            st.error(f"No data found for {symbol} with interval {interval}")
            return None
            
        required_columns = ['Open', 'High', 'Low', 'Close']
        if not all(col in data.columns for col in required_columns):
            st.error(f"Missing required price data for {symbol}")
            return None
            
        if len(data) < 70:
            # Try extending the start date to get more data
            try:
                start_date = pd.Timestamp(start_date) - pd.Timedelta(days=100)
                start_str = start_date.strftime('%Y-%m-%d')
                data = ticker.history(start=start_str, end=end_date, interval=interval)
                
                if len(data) < 70:
                    st.error(f"Not enough data points for {symbol}")
                    return None
            except Exception as e:
                st.error(f"Error fetching extended data: {str(e)}")
                return None
            
        return data

    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None 