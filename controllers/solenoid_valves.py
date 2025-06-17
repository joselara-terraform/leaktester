#!/usr/bin/env python3
"""
Solenoid Valves Controller Module

Provides high-level control functions for pneumatic solenoid valves.
Controls fill and exhaust valves through the relay controller.
"""

import logging
import time
from typing import Optional

# Handle imports for both module use and standalone testing
try:
    from .relay_controller import RelayController
except ImportError:
    # For standalone testing
    from relay_controller import RelayController

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SolenoidValves:
    """
    High-level controller for solenoid valves used in the leak test system.
    
    Provides simple methods to control fill and exhaust operations
    while managing the underlying relay states safely.
    """
    
    def __init__(self, relay_controller: Optional[RelayController] = None):
        """
        Initialize the solenoid valves controller.
        
        Args:
            relay_controller: Existing relay controller instance, or None to create new one
        """
        self.relay_controller = relay_controller or RelayController()
        self._own_relay_controller = relay_controller is None
        
        # Verify required relays are available
        self._verify_relays()
        
        logger.info("SolenoidValves controller initialized")
    
    def _verify_relays(self):
        """Verify that required relays are available."""
        required_relays = ["fill", "exhaust"]
        available_relays = list(self.relay_controller.relays.keys())
        
        for relay_id in required_relays:
            if relay_id not in available_relays:
                raise ValueError(f"Required relay '{relay_id}' not found in relay controller")
        
        logger.info(f"Verified solenoid relays: {required_relays}")
    
    def fill(self, duration: Optional[float] = None) -> bool:
        """
        Open the fill valve to allow pressurization of the DUT.
        
        Args:
            duration: Optional time in seconds to keep valve open.
                     If None, valve stays open until manually closed.
            
        Returns:
            bool: True if successful, False if error
        """
        logger.info(f"Opening fill valve" + (f" for {duration}s" if duration else ""))
        
        try:
            # Turn on fill solenoid
            success = self.relay_controller.set_state("fill", True)
            if not success:
                logger.error("Failed to open fill valve")
                return False
            
            # If duration specified, wait then close automatically
            if duration is not None:
                time.sleep(duration)
                return self.stop_fill()
            
            return True
            
        except Exception as e:
            logger.error(f"Error controlling fill valve: {e}")
            return False
    
    def stop_fill(self) -> bool:
        """
        Close the fill valve to stop pressurization.
        
        Returns:
            bool: True if successful, False if error
        """
        logger.info("Closing fill valve")
        
        try:
            success = self.relay_controller.set_state("fill", False)
            if not success:
                logger.error("Failed to close fill valve")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing fill valve: {e}")
            return False
    
    def exhaust(self, duration: Optional[float] = None) -> bool:
        """
        Open the exhaust valve to depressurize the DUT.
        
        Args:
            duration: Optional time in seconds to keep valve open.
                     If None, valve stays open until manually closed.
            
        Returns:
            bool: True if successful, False if error
        """
        logger.info(f"Opening exhaust valve" + (f" for {duration}s" if duration else ""))
        
        try:
            # Turn on exhaust solenoid
            success = self.relay_controller.set_state("exhaust", True)
            if not success:
                logger.error("Failed to open exhaust valve")
                return False
            
            # If duration specified, wait then close automatically
            if duration is not None:
                time.sleep(duration)
                return self.stop_exhaust()
            
            return True
            
        except Exception as e:
            logger.error(f"Error controlling exhaust valve: {e}")
            return False
    
    def stop_exhaust(self) -> bool:
        """
        Close the exhaust valve to stop depressurization.
        
        Returns:
            bool: True if successful, False if error
        """
        logger.info("Closing exhaust valve")
        
        try:
            success = self.relay_controller.set_state("exhaust", False)
            if not success:
                logger.error("Failed to close exhaust valve")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing exhaust valve: {e}")
            return False
    
    def close_all_valves(self) -> bool:
        """
        Safety function: Close all solenoid valves.
        
        Returns:
            bool: True if all valves closed successfully
        """
        logger.info("Closing all solenoid valves")
        
        fill_success = self.stop_fill()
        exhaust_success = self.stop_exhaust()
        
        success = fill_success and exhaust_success
        
        if success:
            logger.info("All solenoid valves closed successfully")
        else:
            logger.error("Failed to close one or more solenoid valves")
        
        return success
    
    def get_valve_states(self) -> dict:
        """
        Get the current state of all solenoid valves.
        
        Returns:
            dict: Current state of each valve (True=open, False=closed)
        """
        return {
            "fill": self.relay_controller.get_state("fill"),
            "exhaust": self.relay_controller.get_state("exhaust")
        }
    
    def close(self):
        """Clean up resources."""
        logger.info("Closing solenoid valves controller")
        
        # Close all valves before cleanup
        self.close_all_valves()
        
        # Only close relay controller if we created it
        if self._own_relay_controller:
            self.relay_controller.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()

if __name__ == "__main__":
    # Manual solenoid valve control
    print("=== Manual Solenoid Valve Control ===")
    print("Interactive control for testing valve hardware")
    
    try:
        with SolenoidValves() as valves:
            print(f"\nInitial valve states: {valves.get_valve_states()}")
            
            while True:
                print("\n--- Manual Control Menu ---")
                print("1. Toggle FILL valve")
                print("2. Toggle EXHAUST valve") 
                print("3. Show valve states")
                print("4. Close ALL valves (safety)")
                print("5. Exit")
                
                try:
                    choice = input("\nEnter choice (1-5): ").strip()
                    
                    if choice == "1":
                        # Toggle fill valve
                        current_state = valves.get_valve_states()["fill"]
                        new_state = not current_state
                        
                        if new_state:
                            success = valves.fill()
                            action = "OPENED"
                        else:
                            success = valves.stop_fill()
                            action = "CLOSED"
                        
                        if success:
                            print(f"✓ Fill valve {action}")
                        else:
                            print(f"✗ Failed to {action.lower()} fill valve")
                        
                        print(f"Fill valve state: {'OPEN' if valves.get_valve_states()['fill'] else 'CLOSED'}")
                    
                    elif choice == "2":
                        # Toggle exhaust valve
                        current_state = valves.get_valve_states()["exhaust"]
                        new_state = not current_state
                        
                        if new_state:
                            success = valves.exhaust()
                            action = "OPENED"
                        else:
                            success = valves.stop_exhaust()
                            action = "CLOSED"
                        
                        if success:
                            print(f"✓ Exhaust valve {action}")
                        else:
                            print(f"✗ Failed to {action.lower()} exhaust valve")
                        
                        print(f"Exhaust valve state: {'OPEN' if valves.get_valve_states()['exhaust'] else 'CLOSED'}")
                    
                    elif choice == "3":
                        # Show current states
                        states = valves.get_valve_states()
                        print(f"\nCurrent valve states:")
                        print(f"  Fill valve:    {'OPEN' if states['fill'] else 'CLOSED'}")
                        print(f"  Exhaust valve: {'OPEN' if states['exhaust'] else 'CLOSED'}")
                    
                    elif choice == "4":
                        # Close all valves (safety)
                        print("Closing all valves...")
                        success = valves.close_all_valves()
                        if success:
                            print("✓ All valves closed successfully")
                        else:
                            print("✗ Failed to close one or more valves")
                        
                        states = valves.get_valve_states()
                        print(f"Final states: Fill={'CLOSED' if not states['fill'] else 'OPEN'}, Exhaust={'CLOSED' if not states['exhaust'] else 'OPEN'}")
                    
                    elif choice == "5":
                        # Exit
                        print("Closing all valves before exit...")
                        valves.close_all_valves()
                        print("✓ Manual control session ended")
                        break
                    
                    else:
                        print("Invalid choice. Please enter 1-5.")
                
                except KeyboardInterrupt:
                    print("\n\nKeyboard interrupt detected.")
                    print("Closing all valves for safety...")
                    valves.close_all_valves()
                    print("✓ Manual control session ended safely")
                    break
                    
                except Exception as e:
                    print(f"Error: {e}")
                    print("Closing all valves for safety...")
                    valves.close_all_valves()
            
    except Exception as e:
        print(f"✗ Manual solenoid valve control failed: {e}")
        exit(1) 