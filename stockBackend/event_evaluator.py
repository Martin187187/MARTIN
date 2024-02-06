
def evaluate_event(event):
    score = 1
    x = event["latest_price"]
    for c in event["intervals"]:
        score *= x/c["max_price"]
        score *= x/c["min_price"]
    return score
