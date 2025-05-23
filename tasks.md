# 🛠️ MVP Build Plan: EOL Leak Tester

This document outlines each task required to build the MVP for the EOL leak tester. Each task is independent, testable, and focused on a single concern.

---

## Phase 1: Environment Setup

### 1. Create project folder structure
- Create `leak_tester/` with subfolders: `controllers/`, `ui/`, `tests/`, `services/`, `config/`, `data/logs/`

### 2. Create `requirements.txt`
- List dependencies: `gpiozero`, `PyYAML`, `matplotlib`, `Pillow`, `spidev`, etc.

### 3. Set up Raspberry Pi OS, GPIO access, and I2C
- Confirm `gpiozero` access
- Confirm I2C bus is enabled and working (`i2cdetect -y 1`)

### 4. Connect screen and confirm Python GUI display
- Write a test script that opens a simple window on the touchscreen

---

## Phase 2: Relay + SSR Control

### 5. Write and test `relay_controller.py` with mock relay
- Toggle GPIO pin connected to SSR using `RelayController.set_state(relay_id, True/False)`

### 6. Write and test `solenoid_valves.py`
- Functions: `fill()`, `exhaust()`, `isolate()` turn on/off relays via `relay_controller`

### 7. Write and test `cylinders.py`
- Functions: `extend()`, `retract()` control the 5/3 valve solenoids

---

## Phase 3: Pressure Transducer Input

### 8. Wire and confirm ADC module is detected on I2C
- Confirm presence with `i2cdetect`

### 9. Write and test `adc_reader.py`
- Read value from ADC and convert to 4-20mA current

### 10. Calibrate ADC reading to PSI
- Translate current to psi; validate using known pressure source

---

## Phase 4: GUI Development

### 11. Write and test `test_button.py`
- Display a button on screen; print "Test started" on click

### 12. Write and test `main_ui.py`
- UI shows pressure, test phase, result, and includes test button

---

## Phase 5: Test Logic & State Machine

### 13. Write `test_runner.py` framework
- Stub function `run_test()` with logging for phase transitions

### 14. Implement phase: Extend cylinders
- Call `cylinders.extend()`; delay to allow movement

### 15. Implement phase: Fill DUT
- Call `solenoid_valves.fill()` for configured time

### 16. Implement phase: Stabilize
- Wait configured time with all solenoids off

### 17. Implement phase: Record pressure during test
- Start `pressure_logger.start(duration_sec)`

### 18. Implement phase: Isolate DUT
- Close fill and exhaust valves

### 19. Implement phase: Exhaust
- Open `exhaust` solenoid briefly

### 20. Implement phase: Retract cylinders
- Call `cylinders.retract()`; wait for retraction

---

## Phase 6: Result Evaluation

### 21. Write and test `pressure_logger.py`
- Save timestamped psi values to CSV

### 22. Write and test `results_evaluator.py`
- Load pressure data; calculate decay rate; return PASS/FAIL

### 23. Update UI to show "PASS"/"FAIL" result
- Reflect result at end of test on screen

---

## Phase 7: Integration and Final Polish

### 24. Hook UI to `test_runner.run_test()`
- Clicking button starts full test logic

### 25. Display test phase + live pressure during test
- UI updates in real time from state + ADC

### 26. Add error handling for all hardware modules
- Add try/except for I2C and GPIO operations

### 27. Log each test result (time, PASS/FAIL, max psi, decay rate)
- Create summary log in `data/logs/` for each test

### 28. Test full sequence on actual DUT
- Run entire test with real hardware and verify Go/No-Go logic