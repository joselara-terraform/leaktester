#!/usr/bin/env python3
"""
Simple 5/3 Valve Solenoid Controller for Raspberry Pi
"""

import RPi.GPIO as GPIO
import time

class ValveController:
    def __init__(self, extend_pin=17, retract_pin=27):
        """
        Initialize GPIO for valve control
        
        Args:
            extend_pin: GPIO pin for extend solenoid (default 17)
            retract_pin: GPIO pin for retract solenoid (default 27)
        """
        # Use Broadcom (BCM) pin numbering
        GPIO.setmode(GPIO.BCM)
        
        # Setup pins as outputs
        self.extend_pin = extend_pin
        self.retract_pin = retract_pin
        
        GPIO.setup(self.extend_pin, GPIO.OUT)
        GPIO.setup(self.retract_pin, GPIO.OUT)
        
        # Ensure both solenoids start off
        self.stop()
    
    def extend(self, duration=None):
        """
        Activate extend solenoid
        
        Args:
            duration: Time to keep solenoid active (seconds). 
                      If None, stays on until manually stopped.
        """
        # Turn off retract first for safety
        GPIO.output(self.retract_pin, GPIO.LOW)
        
        # Activate extend solenoid
        GPIO.output(self.extend_pin, GPIO.HIGH)
        
        # Wait if duration specified
        if duration:
            time.sleep(duration)
            self.stop()
    
    def retract(self, duration=None):
        """
        Activate retract solenoid
        
        Args:
            duration: Time to keep solenoid active (seconds). 
                      If None, stays on until manually stopped.
        """
        # Turn off extend first for safety
        GPIO.output(self.extend_pin, GPIO.LOW)
        
        # Activate retract solenoid
        GPIO.output(self.retract_pin, GPIO.HIGH)
        
        # Wait if duration specified
        if duration:
            time.sleep(duration)
            self.stop()
    
    def stop(self):
        """
        Stop all solenoid activity (neutral position)
        """
        GPIO.output(self.extend_pin, GPIO.LOW)
        GPIO.output(self.retract_pin, GPIO.LOW)
    
    def cleanup(self):
        """
        Clean up GPIO resources
        """
        GPIO.cleanup()

def main():
    # Example usage
    valve = ValveController()
    
    try:
        # Extend for 2 seconds
        print("Extending...")
        valve.extend(duration=2)
        time.sleep(1)
        
        # Retract for 2 seconds
        print("Retracting...")
        valve.retract(duration=2)
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    finally:
        valve.cleanup()

if __name__ == "__main__":
    main()