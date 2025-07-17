from collections import defaultdict
import time

# For tracking how long targets stay in danger zones
target_loitering_time = defaultdict(float)

# Timestamp of last detection
last_detection_time = time.time()

# For storing alert messages
alerts = []

def reset_alerts():
    """Reset all alert information"""
    global alerts, target_loitering_time, last_detection_time
    alerts = []
    target_loitering_time = defaultdict(float)
    last_detection_time = time.time()

def add_alert(alert_message):
    """Add a new alert message"""
    global alerts
    if alert_message not in alerts:
        alerts.append(alert_message)
        print(f"Alert: {alert_message}")

def get_alerts():
    """Get all current alert messages"""
    return alerts

def update_loitering_time(target_id, time_diff):
    """Update how long a target has been in the danger zone"""
    global target_loitering_time
    target_loitering_time[target_id] += time_diff
    return target_loitering_time[target_id]

def reset_loitering_time(target_id):
    """Reset a target's loitering time"""
    global target_loitering_time
    target_loitering_time[target_id] = 0

def get_loitering_time(target_id):
    """Get a target's loitering time"""
    return target_loitering_time[target_id]

def update_detection_time():
    """Update detection time and return the time difference"""
    global last_detection_time
    current_time = time.time()
    time_diff = current_time - last_detection_time
    last_detection_time = current_time
    return time_diff 