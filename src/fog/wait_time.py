from datetime import datetime

TURNOVER_MINUTES = {
    "breakfast": 45,   # 7am - 11am
    "lunch":     60,   # 11am - 2pm
    "afternoon": 180,  # 2pm - 5pm (studying, etc.)
    "dinner":    75,   # 5pm - 9pm
}

def get_turnover_minutes():
    hour = datetime.now().hour
    if 7 <= hour < 11:
        return TURNOVER_MINUTES["breakfast"]
    elif 11 <= hour < 14:
        return TURNOVER_MINUTES["lunch"]
    elif 14 <= hour < 17:
        return TURNOVER_MINUTES["afternoon"]
    else:
        return TURNOVER_MINUTES["dinner"]

# returns estimated wait time in minutes
def estimate_wait_time(people_waiting: int, total_seats: int) -> float:
    if total_seats == 0:
        return 0.0
    turnover = get_turnover_minutes()
    return round((people_waiting / total_seats) * turnover, 1)