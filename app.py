from flask import Flask, render_template, jsonify, request
import sqlite3
import random
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("water_monitor.db")

# SOFTWARE-ONLY DEMO: these are simulated sensor values, not real measurements.
state = {
    "level": 56.0, "temperature": 27.4, "humidity": 61.0,
    "tds": 280, "ph": 7.1, "turbidity": 1.8,
    "motor": False, "mode": "AUTO",
    "low_threshold": 25, "high_threshold": 90,
    "quality_tds_limit": 500, "quality_turbidity_limit": 5.0,
    "last_updated": None, "alerts": []
}

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, level REAL, temperature REAL,
            humidity REAL, tds INTEGER, ph REAL, turbidity REAL,
            motor TEXT, status TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, severity TEXT, message TEXT
        )""")

def quality_status():
    if state["tds"] > state["quality_tds_limit"] or state["turbidity"] > state["quality_turbidity_limit"] or not (6.5 <= state["ph"] <= 8.5):
        return "POOR"
    return "GOOD"

def evaluate():
    alerts = []
    if state["level"] >= 95:
        alerts.append({"severity": "danger", "message": "Overflow risk: tank level is critically high."})
    elif state["level"] >= state["high_threshold"]:
        alerts.append({"severity": "warning", "message": "Tank is near full. Auto motor stop condition reached."})
    if state["level"] <= state["low_threshold"]:
        alerts.append({"severity": "warning", "message": "Low water level detected."})
    if state["temperature"] >= 40:
        alerts.append({"severity": "warning", "message": "Water temperature is unusually high."})
    if state["temperature"] <= 5:
        alerts.append({"severity": "warning", "message": "Water temperature is unusually low."})
    if state["humidity"] >= 85:
        alerts.append({"severity": "info", "message": "High surrounding humidity detected."})
    if quality_status() == "POOR":
        alerts.append({"severity": "danger", "message": "Poor water quality: check TDS, pH and turbidity readings."})
    state["alerts"] = alerts

    # Simulated automatic control. Overflow protection always stops the motor.
    if state["mode"] == "AUTO":
        if state["level"] >= state["high_threshold"] or state["level"] >= 95:
            state["motor"] = False
        elif state["level"] <= state["low_threshold"]:
            state["motor"] = True

def save_snapshot():
    now = datetime.now().isoformat(timespec="seconds")
    state["last_updated"] = now
    evaluate()
    status = "POOR" if quality_status() == "POOR" else "NORMAL"
    with connect_db() as conn:
        conn.execute("""INSERT INTO history
            (created_at, level, temperature, humidity, tds, ph, turbidity, motor, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, state["level"], state["temperature"], state["humidity"],
             state["tds"], state["ph"], state["turbidity"],
             "ON" if state["motor"] else "OFF", status))

def public_state():
    evaluate()
    return {
        **state,
        "quality": quality_status(),
        "motor_label": "ON" if state["motor"] else "OFF",
        "overflow": state["level"] >= 95,
        "updated": state["last_updated"]
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/status")
def api_status():
    return jsonify(public_state())

@app.post("/api/simulate")
def api_simulate():
    """Move simulated readings slightly to mimic a software demo."""
    state["level"] = round(max(0, min(100, state["level"] + random.uniform(-4, 5))), 1)
    state["temperature"] = round(max(0, min(60, state["temperature"] + random.uniform(-0.6, 0.6))), 1)
    state["humidity"] = round(max(10, min(100, state["humidity"] + random.uniform(-2, 2))), 1)
    state["tds"] = max(0, int(state["tds"] + random.randint(-15, 18)))
    state["ph"] = round(max(0, min(14, state["ph"] + random.uniform(-0.15, 0.15))), 1)
    state["turbidity"] = round(max(0, state["turbidity"] + random.uniform(-0.3, 0.4)), 1)
    evaluate()
    save_snapshot()
    return jsonify(public_state())

@app.post("/api/demo-values")
def api_demo_values():
    """Set readings manually for demonstrations/testing alert conditions."""
    data = request.get_json(silent=True) or {}
    allowed = {"level": (0, 100, float), "temperature": (-10, 80, float),
               "humidity": (0, 100, float), "tds": (0, 5000, int),
               "ph": (0, 14, float), "turbidity": (0, 100, float)}
    for key, (lo, hi, typ) in allowed.items():
        if key in data:
            try:
                state[key] = typ(max(lo, min(hi, float(data[key]))))
            except (TypeError, ValueError):
                return jsonify({"error": f"Invalid value for {key}"}), 400
    evaluate()
    save_snapshot()
    return jsonify(public_state())

@app.post("/api/motor")
def api_motor():
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action == "auto":
        state["mode"] = "AUTO"
        evaluate()
    elif action in ("on", "off"):
        state["mode"] = "MANUAL"
        # Safety interlock: never allow manual ON at overflow/critical-high level.
        if action == "on" and state["level"] >= state["high_threshold"]:
            state["motor"] = False
            return jsonify({"error": "Motor kept OFF for overflow protection. Lower the simulated tank level first.",
                            **public_state()}), 409
        state["motor"] = action == "on"
    else:
        return jsonify({"error": "Use action: on, off, or auto"}), 400
    save_snapshot()
    return jsonify(public_state())

@app.post("/api/settings")
def api_settings():
    data = request.get_json(silent=True) or {}
    try:
        low = int(data.get("low_threshold", state["low_threshold"]))
        high = int(data.get("high_threshold", state["high_threshold"]))
        tds_limit = int(data.get("quality_tds_limit", state["quality_tds_limit"]))
        turbidity_limit = float(data.get("quality_turbidity_limit", state["quality_turbidity_limit"]))
        if not (0 <= low < high <= 100):
            return jsonify({"error": "Thresholds must satisfy 0 ≤ low < high ≤ 100."}), 400
        if tds_limit < 0 or turbidity_limit < 0:
            return jsonify({"error": "Quality limits cannot be negative."}), 400
        state.update(low_threshold=low, high_threshold=high,
                     quality_tds_limit=tds_limit, quality_turbidity_limit=turbidity_limit)
        evaluate()
        save_snapshot()
        return jsonify(public_state())
    except (TypeError, ValueError):
        return jsonify({"error": "Please enter valid numeric settings."}), 400

@app.get("/api/history")
def api_history():
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 20").fetchall()
    return jsonify([dict(row) for row in rows])

@app.get("/api/events")
def api_events():
    evaluate()
    return jsonify(state["alerts"])

init_db()
evaluate()

if __name__ == "__main__":
    save_snapshot()
    app.run(debug=True)
