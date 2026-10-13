# AI Water Monitoring Agent — Software-Only Project

A runnable Flask web application that simulates smart water-tank monitoring and automatic motor control. **No IoT board, sensors, relay, or physical motor is required.** Every sensor reading and motor state is simulated in software.

## Features
- Tank level monitoring and overflow-risk detection
- Simulated water temperature and surrounding humidity
- Water quality indicators: TDS, pH, turbidity, plus configurable warning limits
- Automatic motor logic: ON at/below the low-level threshold, OFF at/above the high-level threshold
- Overflow safety interlock: motor remains OFF at the high threshold, even in manual mode
- Manual ON/OFF and Auto mode controls for demonstration
- Alerts and basic recommendations
- Configurable thresholds
- Test-value control to demonstrate overflow/low-water scenarios
- SQLite reading history that persists between app restarts
- Responsive dashboard

## Requirements
- Python 3.9 or newer
- Flask

## Run on Windows
1. Extract the ZIP file.
2. Open Command Prompt or the VS Code terminal inside the extracted `ai_water_monitoring_agent` folder.
3. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the app:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

## How to demonstrate
1. Click **Run next simulation step** to generate readings and save a history record.
2. Change the test water level to `96` and click **Apply test** to show overflow warning and motor stop.
3. Set the test level to `10`, switch to Auto mode, and the motor simulation should turn ON (if the low threshold is above 10).
4. Set TDS above the configured limit or adjust quality limits to demonstrate a poor-quality alert.
5. Review the Reading History table.

## Important project limitation
This is a software prototype, not a certified water-quality instrument. Values are synthetic and cannot determine whether water is safe to drink. The motor buttons do not control a real pump. Real automatic motor control would require physical sensors, a controller, an appropriately rated relay/contactor, electrical protection, and qualified installation; these are intentionally outside this software-only project.

## Project structure
```text
ai_water_monitoring_agent/
├── app.py
├── requirements.txt
├── README.md
├── water_monitor.db       # created automatically on first run
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```
