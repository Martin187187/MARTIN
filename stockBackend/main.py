import sys
import threading
from datetime import datetime, time, date, timedelta

from fastapi import FastAPI
from pymongo import MongoClient

from date_utility import is_workday, is_in_time_interval, time_until_next_workday_and_interval
from scraper import background_task

app = FastAPI()

# Parse command-line argument for MongoDB host
mongodb_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"

mongo_client = MongoClient(f"mongodb://{mongodb_host}:27017/")
db = mongo_client["stock_database"]
datetime_entries_collection = db["datetime_entries"]
time_interval_collection = db["time_interval"]

# Start a new thread for the background task
background_thread = threading.Thread(target=background_task, daemon=True)


# Your route
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.post("/add_datetime")
async def add_datetime_entry(value: date = datetime.now().date()):
    # Insert the datetime entry into the MongoDB collection

    start_datetime = datetime.combine(value, datetime.now().time())
    datetime_entries_collection.insert_one({"entry": start_datetime})
    return {"message": "Datetime entry added successfully"}


@app.get("/check_valid_date/{date_string}")
async def check_valid_date(value: datetime = datetime.now()) -> bool:
    entries = list(datetime_entries_collection.find({}, {"_id": 0, "entry": 1}))
    entries = [elm['entry'].date() for elm in entries]
    time_interval = time_interval_collection.find_one({}, {"_id": 0})
    return is_workday(value.date(), entries) and is_in_time_interval(value.time(),
                                                                     time_interval['start_datetime'].time(),
                                                                     time_interval['end_datetime'].time())


@app.get("/countdown/{date_string}")
async def check_valid_date(value: datetime = datetime.now()) -> timedelta:
    entries = list(datetime_entries_collection.find({}, {"_id": 0, "entry": 1}))
    entries = [elm['entry'].date() for elm in entries]
    time_interval = time_interval_collection.find_one({}, {"_id": 0})
    return time_until_next_workday_and_interval(value, entries, time_interval['start_datetime'].time(),
                                                time_interval['end_datetime'].time())


# POST endpoint to add a time interval
@app.put("/update_time_interval")
async def add_time_interval(start_time: time = time(15, 30), end_time: time = time(22, 0)):
    # Insert the time interval into the MongoDB collection

    # Get today's date
    today = datetime.now().date()

    # Create datetime objects by combining today's date with the time
    start_datetime = datetime.combine(today, start_time)
    end_datetime = datetime.combine(today, end_time)
    time_interval_collection.update_one(
        {},
        {'$set': {"start_datetime": start_datetime, "end_datetime": end_datetime}},
        upsert=True
    )
    return {"message": "Time interval added successfully"}


# GET endpoint to retrieve all time intervals
@app.get("/get_time_interval")
async def get_time_intervals():
    # Retrieve all time intervals from the MongoDB collection
    time_interval = time_interval_collection.find_one({}, {"_id": 0})
    return {"start_time": time_interval['start_datetime'].time(), "end_time": time_interval['end_datetime'].time()}


if __name__ == "__main__":
    background_thread.start()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
