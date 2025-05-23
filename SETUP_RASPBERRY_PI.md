# Raspberry Pi Setup Instructions

This document provides step-by-step instructions for setting up the EOL Leak Tester on a Raspberry Pi.

## Prerequisites

- Raspberry Pi 4 with Raspberry Pi OS installed
- SSH or direct access to the Pi
- Internet connection for package installation

## 1. Enable I2C Interface

Run the Raspberry Pi configuration tool:

```bash
sudo raspi-config
```

Navigate to:
- **Interface Options** → **I2C** → **Enable**
- **Interface Options** → **SPI** → **Enable** (for ADC)

Reboot when prompted:
```bash
sudo reboot
```

## 2. Install System Dependencies

Install I2C tools and Python development packages:

```bash
sudo apt-get update
sudo apt-get install -y i2c-tools python3-pip python3-dev python3-venv git
```

## 3. Get the Code

Option A - Copy from development machine:
```bash
# Copy the entire project folder to Pi
scp -r /path/to/your/leaktester pi@raspberrypi.local:~/
```

Option B - Clone from repository (if using git):
```bash
cd ~
git clone <your-repository-url> leaktester
```

Option C - Manual setup:
```bash
mkdir ~/leaktester
cd ~/leaktester
# Then copy all files manually
```

## 4. Set up Python Environment

Navigate to project and create virtual environment:

```bash
cd ~/leaktester

# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## 5. Verify Setup

Test GPIO access:
```bash
python3 test_gpio_access.py
```

Test I2C access:
```bash
python3 test_i2c_access.py
```

Scan for I2C devices:
```bash
i2cdetect -y 1
```

Test GUI display:
```bash
cd ~/leaktester
source venv/bin/activate

# Set display to local Pi screen (if running over SSH)
export DISPLAY=:0.0

python3 test_gui_display.py
```

**Note**: If running over SSH and you get "no display name" error:
- Use `export DISPLAY=:0.0` to use the Pi's local display
- Or connect with X11 forwarding: `ssh -X terraformer@raspberrypi.local`
- Or run directly on Pi console (most reliable for touchscreen testing)

## 6. Hardware Permissions

Add the user to GPIO and I2C groups:

```bash
sudo usermod -a -G gpio,i2c,spi terraformer
```

Log out and back in for group changes to take effect.

## Expected Results

- **GPIO Test**: Should show "✓ GPIO access test PASSED"
- **I2C Test**: Should show "✓ I2C bus 1 scan successful" 
- **i2cdetect**: Should show a grid with device addresses (if devices are connected)
- **GUI Test**: Should show a full-screen GUI with "EOL Leak Tester" title, touch test button, touch counter, and platform info

## Troubleshooting

### GPIO Issues
- Ensure user is in `gpio` group
- Verify Raspberry Pi OS is up to date

### I2C Issues
- Ensure I2C is enabled via `raspi-config`
- Check `/dev/i2c-1` exists
- Verify user is in `i2c` group

### Permission Denied Errors
- Ensure user is in proper groups: `gpio`, `i2c`, `spi`
- May need to run with `sudo` for hardware access 