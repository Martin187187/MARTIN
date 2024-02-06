from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List




def calculate_min_max_intervals(stock_data: List[dict]):
    # Ensure the stock_data list is not empty
    if not stock_data:
        return {"latest_timestamp": datetime.now(), "latest_price": 0, "intervals": []}

    # Extract timestamps and prices from the stock_data list
    timestamps = [entry["timestamp"] for entry in stock_data]
    prices = [float(entry["price"]) for entry in stock_data]

    # Calculate the latest timestamp and its corresponding price
    latest_timestamp_index = timestamps.index(max(timestamps))
    latest_timestamp = timestamps[latest_timestamp_index]
    latest_price = prices[latest_timestamp_index]

    # Initialize the result dictionary
    result = {"latest_timestamp": latest_timestamp, "latest_price": latest_price, "intervals":[]}

    # Define the time intervals
    intervals = [5, 10, 15, 20, 60, 120, 240, 360, 720, 1080, 1440]

    # Calculate min and max values for each interval
    for interval_minutes in intervals:
        interval_timedelta = timedelta(minutes=interval_minutes)

        # Calculate the start time for the interval
        start_time = latest_timestamp - interval_timedelta

        # Filter data within the interval
        interval_data = [(price, timestamp) for price, timestamp in zip(prices, timestamps) if
                         start_time <= timestamp <= latest_timestamp]

        # Check if there is data within the interval
        if interval_data:
            min_price = min(interval_data, key=lambda x: x[0])[0]
            max_price = max(interval_data, key=lambda x: x[0])[0]
            past = latest_timestamp - min(interval_data, key=lambda x: x[1])[1]

            result["intervals"].append({
                "min_price": min_price, "max_price": max_price, "past": past
            })

    return result
