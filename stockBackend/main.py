import asyncio
import json
import sys
import threading
from datetime import datetime, time, date, timedelta
from time import sleep
from typing import Set

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse

from date_utility import time_until_next_workday_and_interval, is_workday, is_in_time_interval
from event_evaluator import evaluate_event
from mongodb_manager import MongoDBManager
from scraper import calculate_min_max_intervals

from test import get_stock_data, scrape_stock_news

app = FastAPI()
mongo_manager = MongoDBManager(sys.argv[1] if len(sys.argv) > 1 else "localhost")

background_task_running = False
background_task_progress = 0
max_number = 0
results_dict = {}
evaluation_dict = {}

scraper_url = "scraper:8002" if len(sys.argv) > 1 else "localhost:8002"
update_event = False

def background_task():
    global background_task_running
    global background_task_progress
    global max_number
    global update_event

    while True:
        now = datetime.now()

        # Check if it's time to start the background task (every 5 minutes)
        if now.minute % 1 == 0:
            background_task_running = True
            background_task_progress = 0

            symbols = mongo_manager.get_stored_symbols()
            max_number = len(symbols)
            # Perform the background task (replace this with your actual task logic)
            for symbol in symbols:
                current = datetime.now()
                values = mongo_manager.get_stock_data_within_timedelta(symbol, current, timedelta(days=1))
                result = calculate_min_max_intervals(values)
                results_dict[symbol] = result
                evaluation_dict[symbol] = evaluate_event(result)
                background_task_progress += 1

            background_task_running = False

        update_event = True
        sleep(60)  # Sleep for 1 minute before checking again


background_thread = threading.Thread(target=background_task, daemon=True)

# Your routes

html = """
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <div id='defaultMessage'>Default Message</div>
        <script>
            var ws = new WebSocket("ws://localhost:8001/ws");
            var defaultMessageDiv = document.getElementById('defaultMessage');

            ws.onmessage = function(event) {
                defaultMessageDiv.innerHTML = event.data;
            };

            function sendMessage(event) {
                var input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.post("/add_datetime")
async def add_datetime_entry(value: date = datetime.now().date()):
    mongo_manager.add_datetime_entry(value)
    return {"message": "Datetime entry added successfully"}


@app.get("/check_valid_date/{date_string}")
async def check_valid_date(value: datetime = datetime.now()) -> bool:
    entries, time_interval = mongo_manager.get_datetime_entries_and_time_interval()
    return (
            is_workday(value.date(), entries)
            and is_in_time_interval(
        value.time(),
        time_interval["start_time"],
        time_interval["end_time"],
    )
    )


@app.get("/countdown/{date_string}")
async def countdown_to_next_workday(value: datetime = datetime.now()) -> timedelta:
    entries, time_interval = mongo_manager.get_datetime_entries_and_time_interval()
    return time_until_next_workday_and_interval(
        value, entries, time_interval["start_time"], time_interval["end_time"]
    )


@app.put("/update_time_interval")
async def update_time_interval(start_time: time = time(15, 30), end_time: time = time(22, 0)):
    mongo_manager.update_time_interval(start_time, end_time)
    return {"message": "Time interval updated successfully"}


@app.get("/get_time_interval")
async def get_time_intervals():
    time_interval = mongo_manager.get_time_interval()
    return {"start_time": time_interval["start_time"], "end_time": time_interval["end_time"]}


@app.post("/add_stock_data")
async def add_datetime_entry(value: datetime = datetime.now()):
    mongo_manager.add_nested_stock_data('AAPL', value, 450)


@app.get("/get_stock_data/{stock_symbol}")
async def get_time_intervals(symbol: str):
    result = mongo_manager.get_nested_stock_data(symbol)
    return result

@app.get("/get_stock_news/{stock_symbol}")
async def get_time_intervals(symbol: str):
    result = mongo_manager.get_stock_news(symbol)
    return result


@app.get("/get_appearing_days_and_entries/{stock_name}")
async def get_appearing_days_and_entries_route(stock_name: str):
    results = mongo_manager.get_latest_entries(stock_name)
    return results


@app.get("/stock-data/{stock_name}")
def get_stock_data_within_timedelta(
        stock_name: str,
        end_datetime: datetime = Query(datetime.now(), description="End datetime for the query"),
        timedelta_in_past: timedelta = Query(timedelta(days=1), description="Timedelta in the past")
):
    try:
        results = mongo_manager.get_stock_data_within_timedelta(stock_name, end_datetime, timedelta_in_past)
        return {"stock_data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/stock-news/{stock_name}")
def get_stock_data_within_timedelta(
        stock_name: str,
        end_datetime: datetime = Query(datetime.now(), description="End datetime for the query"),
        timedelta_in_past: timedelta = Query(timedelta(days=1), description="Timedelta in the past")
):
    try:
        results = mongo_manager.get_stock_news_within_timedelta(stock_name, end_datetime, timedelta_in_past)
        return {"stock_news": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/symbols/{symbol}")
def store_symbol(symbol: str):
    stored_symbols = mongo_manager.get_stored_symbols()

    if symbol in stored_symbols:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} already exists")
    try:
        get_stock_data(symbol)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} is not compatible")

    mongo_manager.store_symbol(symbol)
    return {"message": f"Symbol {symbol} stored successfully"}


@app.get("/symbols")
def get_stored_symbols():
    stored_symbols = mongo_manager.get_stored_symbols()
    return {"symbols": stored_symbols}


@app.delete("/symbols/{symbol}")
def delete_symbol(symbol: str):
    mongo_manager.delete_symbol(symbol)
    return {"message": f"Symbol {symbol} deleted successfully"}


@app.get("/event/{symbol}")
async def get_event(symbol: str):
    if symbol in results_dict:
        values = mongo_manager.get_stock_data_within_timedelta(symbol, datetime.now(), timedelta(days=1))
        return {"event": results_dict[symbol], "score": evaluation_dict[symbol], "data": values}
    else:
        return {"error": f"No data available for symbol: {symbol}"}


connected_websockets: Set[WebSocket] = set()
message_counter = 0


async def update_all_websockets():
    backend_status = {"running": background_task_running, "progress": background_task_progress, "max": max_number}
    val = json.dumps(backend_status)
    # Send the updated message to all connected websockets
    for websocket in connected_websockets:
        try:
            await websocket.send_text(val)
        except WebSocketDisconnect:
            # Remove disconnected websockets from the set
            connected_websockets.remove(websocket)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)

    try:
        while True:
            await asyncio.sleep(1)
            await update_all_websockets()

    except WebSocketDisconnect:
        # Remove disconnected websockets from the set
        connected_websockets.remove(websocket)
        await update_all_websockets()

@app.websocket("/te/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await websocket.accept()
    global update_event

    try:
        while True:
            await asyncio.sleep(1)
            if symbol in results_dict and update_event:
                update_event = False
                values = mongo_manager.get_stock_data_within_timedelta(symbol, datetime.now(), timedelta(days=1))
                articles = mongo_manager.get_stock_news_within_timedelta(symbol, datetime.now(), timedelta(days=1))
                val = {"event": results_dict[symbol], "score": evaluation_dict[symbol], "data": values, "articles": articles}
                print(val)
                await websocket.send_text(json.dumps(val, default=str))

    except WebSocketDisconnect:
        # Remove disconnected websockets from the set
        pass
if __name__ == "__main__":
    background_thread.start()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
