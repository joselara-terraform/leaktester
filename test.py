#!/usr/bin/env python3
"""
Simple 5/3 Directional Valve Control for Raspberry Pi
Enhanced with 5-second auto-shutoff timers for safety
"""

import RPi.GPIO as GPIO
import time
import sys
import os
import threading

# Add path for config manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config.config_manager import get_config_manager
    CONFIG_AVAILABLE = True
except ImportError:
    print("Warning: Configuration manager not available, using fallback pins")
    CONFIG_AVAILABLE = False

class ValveController:
    def __init__(self, extend_pin, retract_pin, auto_shutoff_time=5.0):
        """
        Initialize the valve controller with auto-shutoff timers
        
        Args:
            extend_pin: GPIO pin for extend solenoid
            retract_pin: GPIO pin for retract solenoid
            auto_shutoff_time: Auto-shutoff time in seconds (default 5.0)
        """
        # Use Broadcom (BCM) pin numbering
        GPIO.setmode(GPIO.BCM)
        
        # Setup pins as outputs
        self.extend_pin = extend_pin
        self.retract_pin = retract_pin
        self.auto_shutoff_time = auto_shutoff_time
        
        GPIO.setup(self.extend_pin, GPIO.OUT)
        GPIO.setup(self.retract_pin, GPIO.OUT)
        
        # Ensure both solenoids start OFF (HIGH for active-low relays)
        GPIO.output(self.extend_pin, GPIO.HIGH)
        GPIO.output(self.retract_pin, GPIO.HIGH)
        
        # Timer management
        self.extend_timer = None
        self.retract_timer = None
        self.timer_lock = threading.Lock()
        
        print(f"ValveController initialized with {auto_shutoff_time}s auto-shutoff")
    
    def _auto_shutoff_extend(self):
        """Auto-shutoff function for extend valve"""
        print(f"  [TIMER] Extend valve auto-shutoff after {self.auto_shutoff_time}s")
        with self.timer_lock:
            GPIO.output(self.extend_pin, GPIO.HIGH)  # Turn OFF (HIGH for active-low)
            self.extend_timer = None
        print("  [TIMER] Extend valve automatically turned OFF")
    
    def _auto_shutoff_retract(self):
        """Auto-shutoff function for retract valve"""
        print(f"  [TIMER] Retract valve auto-shutoff after {self.auto_shutoff_time}s")
        with self.timer_lock:
            GPIO.output(self.retract_pin, GPIO.HIGH)  # Turn OFF (HIGH for active-low)
            self.retract_timer = None
        print("  [TIMER] Retract valve automatically turned OFF")
    
    def _cancel_timer(self, timer):
        """Cancel a timer if it's running"""
        if timer and timer.is_alive():
            timer.cancel()
            return True
        return False
    
    def activate_extend(self):
        """
        Activate extend solenoid for the specified duration
        Automatically turns off after auto_shutoff_time seconds
        """
        with self.timer_lock:
            # Safety: Ensure retract is off and cancel its timer
            if self.retract_timer:
                self._cancel_timer(self.retract_timer)
                self.retract_timer = None
            GPIO.output(self.retract_pin, GPIO.HIGH)  # Ensure retract is OFF
            
            # Cancel existing extend timer if running
            if self.extend_timer:
                self._cancel_timer(self.extend_timer)
            
            # Check current state
            current_state = GPIO.input(self.extend_pin)
            
            if current_state == GPIO.HIGH:  # Currently OFF
                # Turn ON extend valve
                GPIO.output(self.extend_pin, GPIO.LOW)  # Turn ON (LOW for active-low)
                print(f"✓ Extend valve activated for {self.auto_shutoff_time}s")
                
                # Start auto-shutoff timer
                self.extend_timer = threading.Timer(self.auto_shutoff_time, self._auto_shutoff_extend)
                self.extend_timer.start()
                return True
            else:  # Currently ON
                # Turn OFF extend valve (manual shutoff)
                GPIO.output(self.extend_pin, GPIO.HIGH)  # Turn OFF
                if self.extend_timer:
                    self._cancel_timer(self.extend_timer)
                    self.extend_timer = None
                print("✓ Extend valve manually turned OFF")
                return False
    
    def activate_retract(self):
        """
        Activate retract solenoid for the specified duration
        Automatically turns off after auto_shutoff_time seconds
        """
        with self.timer_lock:
            # Safety: Ensure extend is off and cancel its timer
            if self.extend_timer:
                self._cancel_timer(self.extend_timer)
                self.extend_timer = None
            GPIO.output(self.extend_pin, GPIO.HIGH)  # Ensure extend is OFF
            
            # Cancel existing retract timer if running
            if self.retract_timer:
                self._cancel_timer(self.retract_timer)
            
            # Check current state
            current_state = GPIO.input(self.retract_pin)
            
            if current_state == GPIO.HIGH:  # Currently OFF
                # Turn ON retract valve
                GPIO.output(self.retract_pin, GPIO.LOW)  # Turn ON (LOW for active-low)
                print(f"✓ Retract valve activated for {self.auto_shutoff_time}s")
                
                # Start auto-shutoff timer
                self.retract_timer = threading.Timer(self.auto_shutoff_time, self._auto_shutoff_retract)
                self.retract_timer.start()
                return True
            else:  # Currently ON
                # Turn OFF retract valve (manual shutoff)
                GPIO.output(self.retract_pin, GPIO.HIGH)  # Turn OFF
                if self.retract_timer:
                    self._cancel_timer(self.retract_timer)
                    self.retract_timer = None
                print("✓ Retract valve manually turned OFF")
                return False
    
    def emergency_stop(self):
        """Emergency stop - turn off both valves and cancel all timers"""
        print("🚨 EMERGENCY STOP - Turning off all valves")
        with self.timer_lock:
            # Cancel all timers
            if self.extend_timer:
                self._cancel_timer(self.extend_timer)
                self.extend_timer = None
            if self.retract_timer:
                self._cancel_timer(self.retract_timer)
                self.retract_timer = None
            
            # Turn off both valves
            GPIO.output(self.extend_pin, GPIO.HIGH)
            GPIO.output(self.retract_pin, GPIO.HIGH)
        
        print("✓ Emergency stop completed - all valves OFF")
    
    def get_valve_states(self):
        """Get current valve states and timer status"""
        extend_state = GPIO.input(self.extend_pin) == GPIO.LOW  # LOW = ON for active-low
        retract_state = GPIO.input(self.retract_pin) == GPIO.LOW
        
        extend_timer_active = self.extend_timer and self.extend_timer.is_alive()
        retract_timer_active = self.retract_timer and self.retract_timer.is_alive()
        
        return {
            'extend': {
                'active': extend_state,
                'timer_running': extend_timer_active
            },
            'retract': {
                'active': retract_state,
                'timer_running': retract_timer_active
            }
        }
    
    def cleanup(self):
        """Clean up GPIO settings and cancel timers"""
        print("Cleaning up valve controller...")
        
        # Cancel all timers
        with self.timer_lock:
            if self.extend_timer:
                self._cancel_timer(self.extend_timer)
            if self.retract_timer:
                self._cancel_timer(self.retract_timer)
        
        # Turn off all valves
        GPIO.output(self.extend_pin, GPIO.HIGH)
        GPIO.output(self.retract_pin, GPIO.HIGH)
        
        # Cleanup GPIO
        GPIO.cleanup()
        print("✓ Cleanup completed")

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
    
    # Create controller with 5-second auto-shutoff
    controller = ValveController(extend_pin=extend_pin, retract_pin=retract_pin, auto_shutoff_time=5.0)
    
    try:
        print("\n" + "="*50)
        print("5/3 VALVE CONTROL WITH AUTO-SHUTOFF")
        print("="*50)
        print("• Valves automatically turn OFF after 5 seconds")
        print("• Safety: Only one valve can be active at a time")
        print("• Press same key again to manually turn OFF before timer")
        print("="*50)
        
        while True:
            # Show current status
            states = controller.get_valve_states()
            extend_status = "ON" if states['extend']['active'] else "OFF"
            retract_status = "ON" if states['retract']['active'] else "OFF"
            extend_timer = " (⏱ timer)" if states['extend']['timer_running'] else ""
            retract_timer = " (⏱ timer)" if states['retract']['timer_running'] else ""
            
            print(f"\n--- Current Status ---")
            print(f"Extend:  {extend_status}{extend_timer}")
            print(f"Retract: {retract_status}{retract_timer}")
            
            print("\n--- Commands ---")
            print("1: Activate Extend (5s auto-shutoff)")
            print("2: Activate Retract (5s auto-shutoff)")
            print("s: Emergency Stop (turn off all)")
            print("q: Quit")
            
            choice = input("\nEnter command: ").strip().lower()
            
            if choice == '1':
                activated = controller.activate_extend()
                if activated:
                    print("  ⚠️  Extend valve will automatically turn OFF in 5 seconds")
                    print("  💡 Press '1' again to turn OFF manually before timer expires")
                
            elif choice == '2':
                activated = controller.activate_retract()
                if activated:
                    print("  ⚠️  Retract valve will automatically turn OFF in 5 seconds")
                    print("  💡 Press '2' again to turn OFF manually before timer expires")
                
            elif choice == 's':
                controller.emergency_stop()
                
            elif choice == 'q':
                print("Shutting down...")
                break
                
            else:
                print("❌ Invalid command. Please enter 1, 2, s, or q.")
    
    except KeyboardInterrupt:
        print("\n\n🚨 Keyboard interrupt detected!")
        controller.emergency_stop()
        print("Program terminated by user.")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        controller.emergency_stop()
    
    finally:
        # Cleanup GPIO
        controller.cleanup()

if __name__ == "__main__":
    main()