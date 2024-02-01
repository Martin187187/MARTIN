import sys
import threading
from datetime import datetime, time

from fastapi import FastAPI
from pymongo import MongoClient

from scraper import background_task

tags_metadata = [
    {
        "name": "users",
        "description": "Operations with users. The **login** logic is also here.",
    },
    {
        "name": "items",
        "description": "Manage items. So _fancy_ they have their own docs.",
        "externalDocs": {
            "description": "Items external docs",
            "url": "https://fastapi.tiangolo.com/",
        },
    },
]

app = FastAPI(tags_metadata=tags_metadata)

# Parse command-line argument for MongoDB host
mongodb_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"

# MongoDB connection settings
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

@app.get("/users/", tags=["users"])
async def get_users():
    return [{"name": "Harry"}, {"name": "Ron"}]
# POST endpoint to add datetime entries
@app.post("/add_datetime")
async def add_datetime_entry(entry: datetime):
    # Insert the datetime entry into the MongoDB collection
    datetime_entries_collection.insert_one({"entry": entry})
    return {"message": "Datetime entry added successfully"}


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
