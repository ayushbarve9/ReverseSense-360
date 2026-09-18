#!/usr/bin/env python3
"""
ReverseSense-360: IoT-Based Smart Parking Safety System
Platform: Raspberry Pi (Model 3B+ / 4B)
Hardware: HC-SR04 Ultrasonic Sensor, Pi Camera Module, Active Buzzer, LED Indicator
Cloud: ThingSpeak IoT Platform

Description:
  Continuously monitors proximity to obstacles. When an obstacle is detected within
  the configurable safety threshold:
  1. Activates visual (LED) and audible (Buzzer) warnings.
  2. Captures photographic evidence of the obstacle using the Pi Camera.
  3. Uploads real-time telemetry (distance, alert status, event counter) to ThingSpeak.
"""

import os
import time
import signal
import sys
from datetime import datetime

# Attempt to import Raspberry Pi GPIO; allow mock/testing when running on non-Pi platforms
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    print("[WARN] RPi.GPIO module not available. Running in SIMULATION mode.")

# Attempt to import Picamera2
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

import requests

# ==============================================================================
# CONFIGURATION & PIN ASSIGNMENTS (BCM Mode)
# ==============================================================================
PIN_TRIG = 23      # Pin 16 (Ultrasonic Trigger)
PIN_ECHO = 24      # Pin 18 (Ultrasonic Echo - via 1k/2k voltage divider)
PIN_LED = 18       # Pin 12 (Red Alert LED) [Alternative: GPIO 17, Pin 11]
PIN_BUZZER = 17    # Pin 11 (Active Buzzer) [Alternative: GPIO 27, Pin 13]

# Safety & Timing Parameters
DIST_THRESHOLD_CRITICAL = 10.0   # cm: Immediate collision hazard
DIST_THRESHOLD_WARNING  = 30.0   # cm: Caution / Proximity warning
CAPTURE_COOLDOWN_SEC    = 5.0    # Minimum seconds between camera captures
THINGSPEAK_INTERVAL_SEC = 15.0   # Rate limit for free-tier ThingSpeak API
SAMPLE_DELAY_SEC        = 0.5    # Interval between sensor distance readings

# Storage directory for captured incident photos
IMAGE_DIR = os.path.expanduser("~/parking_images")

# ThingSpeak Cloud Configuration
THINGSPEAK_API_KEY = os.getenv("THINGSPEAK_API_KEY", "YOUR_THINGSPEAK_WRITE_API_KEY")
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# ==============================================================================
# HARDWARE INITIALIZATION
# ==============================================================================
picam = None

def setup_hardware():
    """Initializes GPIO pins and camera interface."""
    global picam
    os.makedirs(IMAGE_DIR, exist_ok=True)

    if GPIO_AVAILABLE:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Ultrasonic pins
        GPIO.setup(PIN_TRIG, GPIO.OUT)
        GPIO.setup(PIN_ECHO, GPIO.IN)

        # Actuator pins
        GPIO.setup(PIN_LED, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)

        # Settle sensor
        GPIO.output(PIN_TRIG, False)
        time.sleep(1.0)
        print("[INFO] GPIO setup complete.")

    if PICAMERA2_AVAILABLE:
        try:
            picam = Picamera2()
            picam.start()
            print("[INFO] Picamera2 initialized successfully.")
        except Exception as e:
            print(f"[WARN] Failed to start Picamera2: {e}")
            picam = None

# ==============================================================================
# SENSING & TELEMETRY FUNCTIONS
# ==============================================================================
def measure_distance(timeout=0.03):
    """
    Measures obstacle distance in centimeters using HC-SR04 with timeout guards.
    Returns:
        float: Distance in cm, or None if timeout occurred.
    """
    if not GPIO_AVAILABLE:
        # Simulated distance for testing on non-Pi environments
        import random
        return round(random.uniform(5.0, 45.0), 2)

    # Emit a 10-microsecond trigger pulse
    GPIO.output(PIN_TRIG, True)
    time.sleep(0.00001)
    GPIO.output(PIN_TRIG, False)

    start_time = time.time()
    pulse_start = start_time
    pulse_end = start_time

    # Wait for echo to go HIGH
    while GPIO.input(PIN_ECHO) == 0:
        pulse_start = time.time()
        if pulse_start - start_time > timeout:
            return None  # Timeout waiting for pulse start

    # Wait for echo to go LOW
    while GPIO.input(PIN_ECHO) == 1:
        pulse_end = time.time()
        if pulse_end - pulse_start > timeout:
            return None  # Timeout waiting for pulse end

    # Distance = (time_elapsed * speed of sound 34300 cm/s) / 2
    elapsed = pulse_end - pulse_start
    distance = (elapsed * 34300.0) / 2.0
    return round(distance, 2)

def set_alerts(active: bool):
    """Controls the visual LED and audible Buzzer state."""
    if GPIO_AVAILABLE:
        GPIO.output(PIN_LED, GPIO.HIGH if active else GPIO.LOW)
        GPIO.output(PIN_BUZZER, GPIO.HIGH if active else GPIO.LOW)

def capture_incident_photo():
    """Captures a timestamped image of the obstacle on proximity violation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(IMAGE_DIR, f"incident_{timestamp}.jpg")

    if picam is not None:
        try:
            picam.capture_file(filepath)
            print(f" [CAMERA] Incident evidence saved via Picamera2: {filepath}")
            return filepath
        except Exception as e:
            print(f"[WARN] Picamera2 capture failed: {e}")

    # Fallback to libcamera-still or raspistill system commands
    for cmd in [f"libcamera-still -o {filepath} --timeout 500 -n", f"raspistill -o {filepath} -t 500 -n"]:
        ret = os.system(cmd)
        if ret == 0:
            print(f" [CAMERA] Incident evidence saved via CLI: {filepath}")
            return filepath

    print(f" [CAMERA] Image capture simulated: {filepath}")
    return filepath

def upload_telemetry(distance, alert_active, event_count):
    """
    Sends telemetry to ThingSpeak cloud via REST API.
    Field 1: Distance (cm)
    Field 2: Alert Status (1 = Active, 0 = Clear)
    Field 3: Total Incident Event Count
    """
    if THINGSPEAK_API_KEY in ("YOUR_THINGSPEAK_WRITE_API_KEY", ""):
        return False

    payload = {
        "api_key": THINGSPEAK_API_KEY,
        "field1": distance,
        "field2": 1 if alert_active else 0,
        "field3": event_count
    }

    try:
        response = requests.post(THINGSPEAK_URL, data=payload, timeout=3.0)
        if response.status_code == 200 and response.text != "0":
            print(f" [CLOUD] Telemetry published to ThingSpeak (Entry #{response.text})")
            return True
        else:
            print(f"[WARN] ThingSpeak update rejected: {response.text}")
    except requests.RequestException as err:
        print(f"[WARN] Cloud upload failed: {err}")
    return False

# ==============================================================================
# MAIN EVENT LOOP & SIGNAL HANDLING
# ==============================================================================
def cleanup_and_exit(signum=None, frame=None):
    """Graceful shutdown handler for Ctrl+C and system termination."""
    print("\n[INFO] Shutting down ReverseSense-360...")
    set_alerts(False)
    if picam is not None:
        try:
            picam.close()
        except Exception:
            pass
    if GPIO_AVAILABLE:
        GPIO.cleanup()
    print("[INFO] Hardware cleanup complete. Safe to exit.")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    setup_hardware()

    last_capture_time = 0.0
    last_cloud_upload = 0.0
    incident_counter = 0

    print("=" * 60)
    print(" ReverseSense-360: IoT Parking Safety System Active")
    print(f" Warning Threshold : {DIST_THRESHOLD_WARNING} cm")
    print(f" Critical Threshold: {DIST_THRESHOLD_CRITICAL} cm")
    print(" Press Ctrl+C to terminate.")
    print("=" * 60)

    while True:
        distance = measure_distance()
        current_time = time.time()

        if distance is None:
            time.sleep(SAMPLE_DELAY_SEC)
            continue

        alert_active = distance < DIST_THRESHOLD_WARNING

        if alert_active:
            print(f"⚠ [ALERT] Object detected within danger zone! Distance: {distance:.2f} cm")
            set_alerts(True)

            # Check if cooldown has elapsed before capturing new snapshot
            if (current_time - last_capture_time) > CAPTURE_COOLDOWN_SEC:
                incident_counter += 1
                capture_incident_photo()
                last_capture_time = current_time
        else:
            print(f"✔ [CLEAR] Distance: {distance:.2f} cm (Safe)")
            set_alerts(False)

        # Upload telemetry to ThingSpeak obeying the 15-second rate limit
        if (current_time - last_cloud_upload) >= THINGSPEAK_INTERVAL_SEC:
            upload_telemetry(distance, alert_active, incident_counter)
            last_cloud_upload = current_time

        time.sleep(SAMPLE_DELAY_SEC)

if __name__ == "__main__":
    main()
