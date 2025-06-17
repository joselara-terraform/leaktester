#!/usr/bin/env python3
"""
Simple 5/3 Directional Valve Control for Raspberry Pi
"""

import RPi.GPIO as GPIO
import time
import sys
import os

# Add path for config manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config.config_manager import get_config_manager
    CONFIG_AVAILABLE = True
except ImportError:
    print("Warning: Configuration manager not available, using fallback pins")
    CONFIG_AVAILABLE = False

class ValveController:
    def __init__(self, extend_pin, retract_pin):
        """
        Initialize the valve controller
        
        Args:
            extend_pin: GPIO pin for extend solenoid
            retract_pin: GPIO pin for retract solenoid
        """
        # Use Broadcom (BCM) pin numbering
        GPIO.setmode(GPIO.BCM)
        
        # Setup pins as outputs
        self.extend_pin = extend_pin
        self.retract_pin = retract_pin
        
        GPIO.setup(self.extend_pin, GPIO.OUT)
        GPIO.setup(self.retract_pin, GPIO.OUT)
        
        # Ensure both solenoids start OFF (HIGH)
        GPIO.output(self.extend_pin, GPIO.HIGH)
        GPIO.output(self.retract_pin, GPIO.HIGH)
    
    def toggle_extend(self):
        """Toggle extend solenoid on/off"""
        current_state = GPIO.input(self.extend_pin)
        GPIO.output(self.extend_pin, not current_state)
        return current_state == GPIO.HIGH
    
    def toggle_retract(self):
        """Toggle retract solenoid on/off"""
        current_state = GPIO.input(self.retract_pin)
        GPIO.output(self.retract_pin, not current_state)
        return current_state == GPIO.HIGH
    
    def cleanup(self):
        """Clean up GPIO settings"""
        GPIO.cleanup()

def main():
    # Load GPIO pin numbers from configuration
    if CONFIG_AVAILABLE:
        try:
            config_manager = get_config_manager()
            gpio_config = config_manager.get_gpio_config()
            extend_pin = gpio_config['extend']
            retract_pin = gpio_config['retract']
            print(f"Using configuration: Extend=GPIO{extend_pin}, Retract=GPIO{retract_pin}")
        except Exception as e:
            print(f"Failed to load configuration: {e}")
            print("Using fallback pin assignments")
            extend_pin = 9
            retract_pin = 10
    else:
        # Fallback pin assignments
        extend_pin = 9
        retract_pin = 10
        print(f"Using fallback pins: Extend=GPIO{extend_pin}, Retract=GPIO{retract_pin}")
    
    controller = ValveController(extend_pin=extend_pin, retract_pin=retract_pin)
    
    try:
        while True:
            print("\n--- 5/3 Valve Control ---")
            print("1: Toggle Extend Solenoid")
            print("2: Toggle Retract Solenoid")
            print("q: Quit")
            
            choice = input("Enter command: ").strip()
            
            if choice == '1':
                state = controller.toggle_extend()
                print(f"Extend Solenoid: {'ON' if state else 'OFF'}")
            elif choice == '2':
                state = controller.toggle_retract()
                print(f"Retract Solenoid: {'ON' if state else 'OFF'}")
            elif choice.lower() == 'q':
                break
            else:
                print("Invalid command. Try again.")
    
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    
    finally:
        # Cleanup GPIO
        controller.cleanup()

if __name__ == "__main__":
    main()