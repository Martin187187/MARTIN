import asyncio
import json
import sys
import threading
from datetime import datetime
from time import sleep
from typing import Set

from fastapi import FastAPI
from starlette.websockets import WebSocket, WebSocketDisconnect

from mongodb_manager import MongoDBManager
from test import get_stock_data, scrape_stock_news
import concurrent.futures
app = FastAPI()
mongo_manager = MongoDBManager(sys.argv[1] if len(sys.argv) > 1 else "localhost")

background_task_running = False
background_task_progress = 0
max_number = 0
new_news = 0
results_dict = {}
update_event = False

def process_symbol(symbol):
    global background_task_progress
    global update_event
    global new_news
    stock_data = get_stock_data(symbol)
    mongo_manager.add_nested_stock_data(symbol, datetime.now(), stock_data)
    stock_news = scrape_stock_news(symbol)
    num = mongo_manager.add_stock_news(symbol, stock_news)
    new_news += num
    background_task_progress += 1
    update_event = True
def background_task():
    global background_task_running
    global background_task_progress
    global max_number
    global update_event
    global new_news

    while True:
        now = datetime.now()

        # Check if it's time to start the background task (every 5 minutes)
        if now.minute % 5 == 0:
            background_task_running = True
            background_task_progress = 0
            new_news = 0

            symbols = mongo_manager.get_stored_symbols()
            max_number = len(symbols)
            update_event = True
            # Perform the background task (replace this with your actual task logic)
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
                executor.map(process_symbol, symbols)

            background_task_running = False
            update_event = True

        sleep(60)  # Sleep for 1 minute before checking again


background_thread = threading.Thread(target=background_task, daemon=True)

connected_websockets: Set[WebSocket] = set()
async def update_all_websockets():
    backend_status = {"running": background_task_running, "progress": background_task_progress, "max": max_number, "new_news": new_news}
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
    global update_event
    await websocket.accept()
    connected_websockets.add(websocket)

    try:
        while True:

            if update_event:
                update_event = False
                await update_all_websockets()
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        # Remove disconnected websockets from the set
        connected_websockets.remove(websocket)
        await update_all_websockets()
if __name__ == "__main__":
    background_thread.start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
