EOL Leak Tester System Architecture
Overview
This document describes the architecture of the End-of-Line (EOL) Leak Tester system, including folder structure, system components, and their responsibilities. The tester is built around a Raspberry Pi 4 and integrates pneumatic actuation, pressure sensing, and touchscreen-based operator control using Python.

🗂️ File and Folder Structure
plaintext
Copy
Edit
leak_tester/
│
├── config/
│   └── settings.yaml            # Configuration for solenoid GPIOs, ADC channels, test parameters, etc.
│
├── controllers/
│   ├── relay_controller.py      # Interface to GPIO-controlled relays triggering SSRs
│   ├── adc_reader.py            # Reads and converts 4-20mA analog signal from pressure transducer
│   ├── solenoid_valves.py       # Controls fill, exhaust, isolate solenoids
│   └── cylinders.py             # Extends/retracts pneumatic pistons via 5/3 valve solenoids
│
├── ui/
│   ├── main_ui.py               # Launches and manages the touchscreen user interface
│   └── test_button.py           # Button widget logic to start test
│
├── tests/
│   └── leak_test.py             # Implements test sequence: fill, stabilize, test, exhaust, evaluate
│
├── services/
│   ├── test_runner.py           # Orchestrates the full test state machine
│   ├── pressure_logger.py       # Records timestamped pressure data during test
│   └── results_evaluator.py     # Compares decay rate to spec and determines pass/fail
│
├── data/
│   └── logs/                    # CSV or JSON logs for each test
│
├── main.py                      # Entry point; initializes all services, loads config, launches UI
└── requirements.txt             # Python dependencies
🧠 System Responsibilities
main.py
Loads configuration from config/settings.yaml

Initializes all controller and service objects

Launches GUI (main_ui.py)

Starts main event loop

🧩 Components and Responsibilities
controllers/
Hardware control abstraction.

relay_controller.py
Controls the GPIO pins tied to SSR inputs for all solenoids.

adc_reader.py
Reads raw values from the I2C ADC module and converts to pressure in psi using calibration.

solenoid_valves.py
Methods: fill(), exhaust(), isolate() — activates respective GPIOs through the relay controller.

cylinders.py
Methods: extend(), retract() — controls 5/3 valve solenoids.

ui/
Handles user interaction.

main_ui.py
Touchscreen interface showing live pressure, test phase, and Go/No-Go result.

test_button.py
Defines the button that starts a new test and calls test_runner.run_test().

tests/
Encapsulates leak test procedure.

leak_test.py
Steps:

Extend cylinders

Fill DUT

Stabilize

Isolate

Test (record pressure)

Evaluate decay

Exhaust

Retract cylinders

services/
Long-lived background services.

test_runner.py
Executes state machine that controls test procedure and interacts with all hardware modules.

pressure_logger.py
Captures pressure over time, saves to file in data/logs/.

results_evaluator.py
Calculates decay rate and checks against limit from config. Returns Go/No-Go status.

config/
System settings.

settings.yaml
Contains:

GPIO pin mappings

ADC channel info

Test timing (fill time, stabilize time, test duration)

Acceptable leak rate threshold

📊 Where State Lives
State	Owner Module	Persistence
Current test phase	test_runner.py	In-memory FSM
Pressure over time	pressure_logger.py	CSV in /data/logs/
Go/No-Go result	results_evaluator.py	Temporary / UI
Config and parameters	settings.yaml	On-disk YAML

🔗 Connections Between Services
plaintext
Copy
Edit
[UI Button Press]
        ↓
  test_runner.run_test()
        ↓
 [State transitions: fill → stabilize → test → exhaust]
        ↓                           ↓
 solenoid_valves, cylinders     pressure_logger.record()
        ↓                           ↓
      hardware                 data/logs/<timestamp>.csv
        ↓                           ↓
     results_evaluator ←────────────┘
        ↓
     UI.display_result()
✅ Summary
This architecture ensures:

Modular Python code

Clear separation of UI, hardware, and logic

Easy debugging and future upgrades (e.g., MQTT, database logging, etc.)

Robustness against test state corruption

Use main.py as the single entry point and keep logic in stateful services while controllers only handle GPIO/ADC interactions.