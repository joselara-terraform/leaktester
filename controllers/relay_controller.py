#!/usr/bin/env python3
"""
Relay Controller Module

Controls GPIO pins connected to Solid State Relays (SSRs).
Provides hardware abstraction for relay control with mock support for development.
"""

import platform
import time
import logging
from typing import Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

class RelayController:
    """
    Controls GPIO pins connected to SSRs for solenoid valve control.
    
    Each relay is identified by a relay_id and controls a specific GPIO pin.
    Provides mock functionality for development on non-Pi systems.
    """
    
    def __init__(self, relay_config: Optional[Dict[str, int]] = None):
        """
        Initialize the relay controller.
        
        Args:
            relay_config: Dictionary mapping relay_id to GPIO pin number
                         Example: {"fill": 18, "exhaust": 19, "isolate": 20}
        """
        # Default relay configuration if none provided
        self.relay_config = relay_config or {
            "fill": 24,      # Fill solenoid (swapped from 23)
            "exhaust": 23,   # Exhaust solenoid (swapped from 24)
            "extend": 9,     # Cylinder extend solenoid (swapped from 10)
            "retract": 10    # Cylinder retract solenoid (swapped from 9)
        }
        
        self.is_pi = is_raspberry_pi()
        self.relays = {}  # Will store relay objects
        self.relay_states = {}  # Track current states
        
        # Initialize relay hardware
        self._initialize_relays()
        
        logger.info(f"RelayController initialized on {'Pi' if self.is_pi else 'development'} system")
        logger.info(f"Relay configuration: {self.relay_config}")
    
    def _initialize_relays(self):
        """Initialize GPIO pins for relay control."""
        if self.is_pi:
            try:
                from gpiozero import DigitalOutputDevice
                
                # Initialize each relay with active_low=True for typical relay modules
                # This means relay.on() sets GPIO LOW, which energizes most relay boards
                for relay_id, gpio_pin in self.relay_config.items():
                    relay = DigitalOutputDevice(gpio_pin, active_high=False, initial_value=False)
                    self.relays[relay_id] = relay
                    self.relay_states[relay_id] = False
                    logger.info(f"Initialized relay '{relay_id}' on GPIO {gpio_pin} (active_low)")
                    
            except ImportError as e:
                logger.error(f"Failed to import gpiozero: {e}")
                self._use_mock_relays()
        else:
            self._use_mock_relays()
    
    def _use_mock_relays(self):
        """Use mock relays for development."""
        logger.info("Using mock relays for development (active_low logic)")
        
        class MockRelay:
            def __init__(self, gpio_pin):
                self.gpio_pin = gpio_pin
                self.value = False  # Tracks the logical state (True=energized, False=de-energized)
                self.gpio_state = True  # Tracks actual GPIO state (inverted for active_low)
                
            def on(self):
                """Turn relay ON (energize) - sets GPIO LOW for active_low"""
                self.value = True
                self.gpio_state = False  # GPIO LOW = Relay ON
                
            def off(self):
                """Turn relay OFF (de-energize) - sets GPIO HIGH for active_low"""
                self.value = False
                self.gpio_state = True  # GPIO HIGH = Relay OFF
                
            def close(self):
                pass
        
        # Create mock relays
        for relay_id, gpio_pin in self.relay_config.items():
            self.relays[relay_id] = MockRelay(gpio_pin)
            self.relay_states[relay_id] = False
            logger.info(f"Mock relay '{relay_id}' on GPIO {gpio_pin} (active_low)")
    
    def set_state(self, relay_id: str, state: bool) -> bool:
        """
        Set the state of a specific relay.
        
        Args:
            relay_id: Identifier for the relay (e.g., "fill", "exhaust")
            state: True to turn on (energize), False to turn off
            
        Returns:
            bool: True if successful, False if error
        """
        if relay_id not in self.relays:
            logger.error(f"Relay '{relay_id}' not found. Available relays: {list(self.relays.keys())}")
            return False
        
        try:
            relay = self.relays[relay_id]
            
            if state:
                relay.on()
                action = "ON"
            else:
                relay.off()
                action = "OFF"
            
            self.relay_states[relay_id] = state
            
            gpio_pin = self.relay_config[relay_id]
            logger.info(f"Relay '{relay_id}' (GPIO {gpio_pin}) turned {action}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set relay '{relay_id}' to {state}: {e}")
            return False
    
    def get_state(self, relay_id: str) -> Optional[bool]:
        """
        Get the current state of a relay.
        
        Args:
            relay_id: Identifier for the relay
            
        Returns:
            bool: Current state (True=on, False=off), None if relay not found
        """
        return self.relay_states.get(relay_id)
    
    def get_all_states(self) -> Dict[str, bool]:
        """
        Get the current state of all relays.
        
        Returns:
            Dict mapping relay_id to current state
        """
        return self.relay_states.copy()
    
    def turn_off_all(self) -> bool:
        """
        Turn off all relays (safety function).
        
        Returns:
            bool: True if all relays turned off successfully
        """
        logger.info("Turning off all relays")
        success = True
        
        for relay_id in self.relays:
            if not self.set_state(relay_id, False):
                success = False
        
        return success
    
    def close(self):
        """Clean up GPIO resources."""
        logger.info("Closing relay controller")
        
        # Turn off all relays before closing
        self.turn_off_all()
        
        # Close GPIO resources
        for relay_id, relay in self.relays.items():
            try:
                relay.close()
            except Exception as e:
                logger.error(f"Error closing relay '{relay_id}': {e}")
        
        self.relays.clear()
        self.relay_states.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()

if __name__ == "__main__":
    # Test the relay controller
    print("=== Relay Controller Test ===")
    
    try:
        with RelayController() as controller:
            print(f"Available relays: {list(controller.relays.keys())}")
            
            # Test each relay
            for relay_id in controller.relays:
                print(f"\nTesting relay: {relay_id}")
                
                # Turn on
                success = controller.set_state(relay_id, True)
                print(f"  Turn ON: {'✓' if success else '✗'}")
                print(f"  State: {controller.get_state(relay_id)}")
                time.sleep(0.5)
                
                # Turn off
                success = controller.set_state(relay_id, False)
                print(f"  Turn OFF: {'✓' if success else '✗'}")
                print(f"  State: {controller.get_state(relay_id)}")
                time.sleep(0.5)
            
            # Test all states
            print(f"\nAll relay states: {controller.get_all_states()}")
            
            # Test turn off all
            controller.set_state("fill", True)
            controller.set_state("exhaust", True)
            print(f"Before turn_off_all: {controller.get_all_states()}")
            
            controller.turn_off_all()
            print(f"After turn_off_all: {controller.get_all_states()}")
            
            print("\n✓ Relay controller test completed successfully")
            
    except Exception as e:
        print(f"✗ Relay controller test failed: {e}")
        exit(1) 