from collections import defaultdict
from typing import List

from pymongo import MongoClient, DESCENDING
from datetime import datetime, time, timedelta


class MongoDBManager:
    def __init__(self, mongodb_host="localhost", database_name="stock_database"):
        self.mongo_client = MongoClient(f"mongodb://{mongodb_host}:27017/")
        self.db = self.mongo_client[database_name]
        self.datetime_entries_collection = self.db["datetime_entries"]
        self.time_interval_collection = self.db["time_interval"]

    def add_datetime_entry(self, value):
        start_datetime = datetime.combine(value, datetime.now().time())
        self.datetime_entries_collection.insert_one({"entry": start_datetime})

    def get_datetime_entries(self):
        entries = list(self.datetime_entries_collection.find({}, {"_id": 0, "entry": 1}))
        return [elm['entry'].date() for elm in entries]

    def update_time_interval(self, start_time, end_time):
        today = datetime.now().date()
        start_datetime = datetime.combine(today, start_time)
        end_datetime = datetime.combine(today, end_time)
        self.time_interval_collection.update_one(
            {},
            {'$set': {"start_datetime": start_datetime, "end_datetime": end_datetime}},
            upsert=True
        )

    def get_time_interval(self):
        time_interval = self.time_interval_collection.find_one({}, {"_id": 0})
        return {
            "start_time": time_interval['start_datetime'].time(),
            "end_time": time_interval['end_datetime'].time()
        }

    def get_datetime_entries_and_time_interval(self):
        entries = self.get_datetime_entries()
        time_interval = self.get_time_interval()
        return entries, time_interval

    def add_stock_news(self, stock_name: str, data):
        num = 0
        collection_name = f"stock_news_{stock_name}"
        stock_data_collection = self.db[collection_name]
        # Check if the title is new
        for elm in data:
            if stock_data_collection.find_one({'title': elm['title']}) is None:
                # Insert new data
                stock_data_collection.insert_one(elm)
                num += 1
        return num

    def get_stock_news(self, stock_name: str):
        collection_name = f"stock_news_{stock_name}"
        stock_data_collection = self.db[collection_name]

        # Find all documents in the collection
        results = list(stock_data_collection.find({}, {"_id": 0}))

        return results

    def get_stock_news_within_timedelta(self, stock_name: str, end_datetime: datetime, timedelta_in_past: timedelta) -> List[dict]:
        collection_name = f"stock_news_{stock_name}"
        stock_data_collection = self.db[collection_name]

        start_datetime = end_datetime - timedelta_in_past

        # Query to retrieve documents within the specified timedelta in the past
        query = {
            "time": {"$gte": start_datetime, "$lte": end_datetime}
        }

        # Find documents that match the query
        results = list(stock_data_collection.find(query, {"_id": 0}))

        return results
    def add_nested_stock_data(self, stock_name: str, timestamp: datetime, price: float):
        collection_name = f"stock_data_{stock_name}"
        stock_data_collection = self.db[collection_name]

        stock_entry = {
            "timestamp": timestamp,
            "price": price
        }
        stock_data_collection.insert_one(stock_entry)
        return {"message": f"Nested stock data for {stock_name} added successfully"}

    def get_nested_stock_data(self, stock_name: str) -> List[dict]:
        collection_name = f"stock_data_{stock_name}"
        stock_data_collection = self.db[collection_name]

        # Find all documents in the collection
        results = list(stock_data_collection.find({}, {"_id": 0}))

        return results

    def get_stock_data_within_timedelta(self, stock_name: str, end_datetime: datetime, timedelta_in_past: timedelta) -> \
            List[dict]:
        collection_name = f"stock_data_{stock_name}"
        stock_data_collection = self.db[collection_name]

        start_datetime = end_datetime - timedelta_in_past

        # Query to retrieve documents within the specified timedelta in the past
        query = {
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        }

        # Find documents that match the query
        results = list(stock_data_collection.find(query, {"_id": 0}))

        return results

    def get_latest_entries(self, stock_name: str) -> List[dict]:
        collection_name = f"stock_data_{stock_name}"
        stock_data_collection = self.db[collection_name]

        # Aggregate by date and count the entries
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$timestamp"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id",
                    "entry_count": "$count"
                }
            }
        ]


        collection_name2 = f"stock_news_{stock_name}"
        stock_data_collection2 = self.db[collection_name2]

        pipeline2 = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$time"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id",
                    "article_count": "$count"
                }
            }
        ]

        # Execute the aggregation pipeline
        a = list(stock_data_collection.aggregate(pipeline))
        b = list(stock_data_collection2.aggregate(pipeline2))
        merged_dict = defaultdict(lambda: {'entry_count': 0, 'article_count': 0})

        # Add entries from the first list
        for entry in a:
            merged_dict[entry['date']].update(entry)

        # Add entries from the second list
        for entry in b:
            merged_dict[entry['date']].update(entry)

        # Convert the dictionary back to a list
        merged_list = [{'date': date, **entries} for date, entries in merged_dict.items()]

        return merged_list

    def get_latest_stock_data(self, stock_name: str) -> dict:
        collection_name = f"stock_data_{stock_name}"
        stock_data_collection = self.db[collection_name]

        # Find the document with the latest timestamp for the given stock
        latest_data = stock_data_collection.find_one(
            filter={},
            sort=[("timestamp", DESCENDING)]
        )

        return latest_data if latest_data else {"message": f"No data available for {stock_name}"}

    def store_symbol(self, symbol: str):
        symbol_collection = self.db["symbols"]
        symbol_collection.update_one(
            {"symbol": symbol},
            {"$set": {"symbol": symbol}},
            upsert=True
        )

    def get_stored_symbols(self) -> List[str]:
        symbol_collection = self.db["symbols"]
        symbols = list(symbol_collection.find({}, {"_id": 0, "symbol": 1}))
        return [symbol['symbol'] for symbol in symbols]

    def delete_symbol(self, symbol: str):
        symbol_collection = self.db["symbols"]
        symbol_collection.delete_one({"symbol": symbol})
