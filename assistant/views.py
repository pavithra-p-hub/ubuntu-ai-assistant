from django.shortcuts import render
from django.conf import settings
import anthropic
from django.conf import settings
import psutil
import platform
from datetime import datetime
from django.utils import timezone
import webbrowser
import requests

client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY
)

def get_system_status():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu": cpu,
        "ram": memory.percent,
        "disk": disk.percent,
    }

def get_system_info():
    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "release": platform.release(),
        "python": platform.python_version(),
    }

def get_battery_status():
    battery = psutil.sensors_battery()

    if battery is None:
        return "Battery information is not available."

    return f"Battery: {battery.percent}%"

def get_disk_space():
    disk = psutil.disk_usage("/")

    total = round(disk.total / (1024 ** 3), 2)
    used = round(disk.used / (1024 ** 3), 2)
    free = round(disk.free / (1024 ** 3), 2)

    return (
        f"Total: {total} GB<br>"
        f"Used: {used} GB<br>"
        f"Free: {free} GB<br>"
        f"Usage: {disk.percent}%"
    )

def get_running_processes():
    processes = []

    for process in psutil.process_iter(["pid", "name"]):
        try:
            info = process.info
            processes.append(
                f"PID: {info['pid']} - {info['name']}"
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return "<br>".join(processes[:10])

def list_files():
    import os

    files = os.listdir(".")

    if not files:
        return "No files or folders found."

    return "<br>".join(files[:20])

def search_files(filename):
    import os

    matches = []

    for root, dirs, files in os.walk("."):
        for file in files:
            if filename.lower() in file.lower():
                matches.append(os.path.join(root, file))

            if len(matches) >= 20:
                return "<br>".join(matches)

    if matches:
        return "<br>".join(matches)

    return f"No files found matching: {filename}"

def get_wifi_status():
    import subprocess

    result = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"],
        capture_output=True,
        text=True
    )

    for line in result.stdout.splitlines():
        parts = line.split(":")

        if len(parts) >= 4 and parts[2] == "connected":
            device = parts[0]
            connection = parts[3]

            if device != "lo":
                return f"Connected: {device}<br>Connection: {connection}"

    return "No active network connection found."

    for line in result.stdout.splitlines():
        if line.startswith("yes:"):
            ssid = line.split(":", 1)[1]
            return f"Connected Wi-Fi: {ssid}"

    return "No Wi-Fi connection found."

def ask_local_ai(user_message):
    if settings.GEMINI_API_KEY:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers={
                "x-goog-api-key": settings.GEMINI_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": user_message}
                        ]
                    }
                ]
            },
            timeout=60
        )

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:1.5b",
            "prompt": user_message,
            "stream": False,
            "options": {
                "num_predict": 100
            }
        },
        timeout=60
    )

    data = response.json()
    return data["response"]

def home(request):
    response = None

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if user_message:
            command = user_message.lower()

            if command == "current time":
                current_time = timezone.localtime().strftime("%I:%M:%S %p")
                response = f"Current time: {current_time}"

            elif command == "system status":
                status = get_system_status()
                response = (
                    f"CPU Usage: {status['cpu']}%<br>"
                    f"RAM Usage: {status['ram']}%<br>"
                    f"Disk Usage: {status['disk']}%"
                )

            elif command == "system info":
                info = get_system_info()
                response = (
                    f"Hostname: {info['hostname']}<br>"
                    f"OS: {info['os']}<br>"
                    f"Release: {info['release']}<br>"
                    f"Python: {info['python']}"
                )

            elif command == "battery status":
                response = get_battery_status()

            elif command == "wifi status":
                response = get_wifi_status()

            elif command == "internet status":
                response = "Internet: Connected"

            elif command == "disk space":
                response = get_disk_space()

            elif command == "running processes":
                response = get_running_processes()

            elif command == "list files":
                response = list_files()

            elif command.startswith("search file "):
                filename = command.replace("search file ", "", 1).strip()

                if filename:
                    response = search_files(filename)
                else:
                    response = "Please provide a filename to search."

            elif command.startswith("open website "):
                website = command.replace("open website ", "", 1).strip()

                if website:
                    if not website.startswith(("http://", "https://")):
                        website = "https://" + website

                    webbrowser.open(website)
                    response = f"Opening: {website}"
                else:
                    response = "Please provide a website."

            else:
                response = ask_local_ai(user_message)

    return render(
        request,
        "assistant/index.html",
        {"response": response}
    )
