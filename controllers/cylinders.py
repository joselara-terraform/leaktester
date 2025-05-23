#!/usr/bin/env python3
"""
Pneumatic Cylinders Controller Module

Provides high-level control functions for pneumatic cylinders.
Controls extend and retract operations through 5/3 valve solenoids.
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

class Cylinders:
    """
    High-level controller for pneumatic cylinders used in the leak test system.
    
    Provides safe control of cylinder extend/retract operations using 5/3 valve solenoids.
    Ensures only one solenoid is active at a time for safety.
    """
    
    def __init__(self, relay_controller: Optional[RelayController] = None):
        """
        Initialize the cylinders controller.
        
        Args:
            relay_controller: Existing relay controller instance, or None to create new one
        """
        self.relay_controller = relay_controller or RelayController()
        self._own_relay_controller = relay_controller is None
        
        # Verify required relays are available
        self._verify_relays()
        
        # Track current cylinder state
        self._current_state = "unknown"  # "extended", "retracted", "moving", "unknown"
        
        logger.info("Cylinders controller initialized")
    
    def _verify_relays(self):
        """Verify that required relays are available."""
        required_relays = ["extend", "retract"]
        available_relays = list(self.relay_controller.relays.keys())
        
        for relay_id in required_relays:
            if relay_id not in available_relays:
                raise ValueError(f"Required relay '{relay_id}' not found in relay controller")
        
        logger.info(f"Verified cylinder relays: {required_relays}")
    
    def _ensure_safe_state(self):
        """Ensure both solenoids are off before any operation (safety)."""
        self.relay_controller.set_state("extend", False)
        self.relay_controller.set_state("retract", False)
        time.sleep(0.1)  # Brief pause to ensure relays have switched
    
    def extend(self, duration: Optional[float] = None, auto_timeout: float = 10.0) -> bool:
        """
        Extend the pneumatic cylinders.
        
        Args:
            duration: Optional time in seconds to energize extend solenoid.
                     If None, uses auto_timeout for safety.
            auto_timeout: Maximum time to keep solenoid energized (safety feature)
            
        Returns:
            bool: True if successful, False if error
        """
        extend_time = duration if duration is not None else auto_timeout
        logger.info(f"Extending cylinders for {extend_time}s")
        
        try:
            # Safety: Ensure clean state
            self._ensure_safe_state()
            
            # Set state to moving
            self._current_state = "moving"
            
            # Energize extend solenoid
            success = self.relay_controller.set_state("extend", True)
            if not success:
                logger.error("Failed to energize extend solenoid")
                self._current_state = "unknown"
                return False
            
            # Wait for movement
            time.sleep(extend_time)
            
            # Turn off extend solenoid
            self.relay_controller.set_state("extend", False)
            
            # Update state
            self._current_state = "extended"
            logger.info("Cylinders extended successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error extending cylinders: {e}")
            self._ensure_safe_state()
            self._current_state = "unknown"
            return False
    
    def retract(self, duration: Optional[float] = None, auto_timeout: float = 10.0) -> bool:
        """
        Retract the pneumatic cylinders.
        
        Args:
            duration: Optional time in seconds to energize retract solenoid.
                     If None, uses auto_timeout for safety.
            auto_timeout: Maximum time to keep solenoid energized (safety feature)
            
        Returns:
            bool: True if successful, False if error
        """
        retract_time = duration if duration is not None else auto_timeout
        logger.info(f"Retracting cylinders for {retract_time}s")
        
        try:
            # Safety: Ensure clean state
            self._ensure_safe_state()
            
            # Set state to moving
            self._current_state = "moving"
            
            # Energize retract solenoid
            success = self.relay_controller.set_state("retract", True)
            if not success:
                logger.error("Failed to energize retract solenoid")
                self._current_state = "unknown"
                return False
            
            # Wait for movement
            time.sleep(retract_time)
            
            # Turn off retract solenoid
            self.relay_controller.set_state("retract", False)
            
            # Update state
            self._current_state = "retracted"
            logger.info("Cylinders retracted successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error retracting cylinders: {e}")
            self._ensure_safe_state()
            self._current_state = "unknown"
            return False
    
    def stop(self) -> bool:
        """
        Emergency stop: Turn off both solenoids immediately.
        
        Returns:
            bool: True if successful, False if error
        """
        logger.info("Emergency stop - turning off all cylinder solenoids")
        
        try:
            extend_success = self.relay_controller.set_state("extend", False)
            retract_success = self.relay_controller.set_state("retract", False)
            
            success = extend_success and retract_success
            
            if success:
                self._current_state = "stopped"
                logger.info("All cylinder solenoids turned off")
            else:
                logger.error("Failed to turn off one or more cylinder solenoids")
                self._current_state = "unknown"
            
            return success
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")
            self._current_state = "unknown"
            return False
    
    def get_state(self) -> str:
        """
        Get the current state of the cylinders.
        
        Returns:
            str: Current state ("extended", "retracted", "moving", "stopped", "unknown")
        """
        return self._current_state
    
    def get_solenoid_states(self) -> dict:
        """
        Get the current state of cylinder solenoids.
        
        Returns:
            dict: Current state of each solenoid (True=energized, False=off)
        """
        return {
            "extend": self.relay_controller.get_state("extend"),
            "retract": self.relay_controller.get_state("retract")
        }
    
    def is_safe_state(self) -> bool:
        """
        Check if cylinders are in a safe state (no solenoids energized).
        
        Returns:
            bool: True if safe (both solenoids off), False otherwise
        """
        states = self.get_solenoid_states()
        return not states["extend"] and not states["retract"]
    
    def close(self):
        """Clean up resources."""
        logger.info("Closing cylinders controller")
        
        # Ensure safe state before cleanup
        self.stop()
        
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
    # Test the cylinders controller
    print("=== Cylinders Controller Test ===")
    
    try:
        with Cylinders() as cylinders:
            print(f"Initial cylinder state: {cylinders.get_state()}")
            print(f"Initial solenoid states: {cylinders.get_solenoid_states()}")
            print(f"Safe state: {cylinders.is_safe_state()}")
            
            # Test extend operation
            print("\n--- Testing Extend Operation ---")
            
            print("Extending cylinders (2 seconds)...")
            success = cylinders.extend(duration=2.0)
            print(f"Extend operation: {'✓' if success else '✗'}")
            print(f"Cylinder state: {cylinders.get_state()}")
            print(f"Solenoid states: {cylinders.get_solenoid_states()}")
            print(f"Safe state: {cylinders.is_safe_state()}")
            
            time.sleep(1)
            
            # Test retract operation
            print("\n--- Testing Retract Operation ---")
            
            print("Retracting cylinders (2 seconds)...")
            success = cylinders.retract(duration=2.0)
            print(f"Retract operation: {'✓' if success else '✗'}")
            print(f"Cylinder state: {cylinders.get_state()}")
            print(f"Solenoid states: {cylinders.get_solenoid_states()}")
            print(f"Safe state: {cylinders.is_safe_state()}")
            
            time.sleep(1)
            
            # Test safety stop
            print("\n--- Testing Safety Features ---")
            
            # Start an extend operation
            print("Starting extend operation...")
            cylinders.relay_controller.set_state("extend", True)
            cylinders._current_state = "moving"
            print(f"Solenoid states during extend: {cylinders.get_solenoid_states()}")
            print(f"Safe state: {cylinders.is_safe_state()}")
            
            # Emergency stop
            print("Testing emergency stop...")
            success = cylinders.stop()
            print(f"Emergency stop: {'✓' if success else '✗'}")
            print(f"Cylinder state: {cylinders.get_state()}")
            print(f"Solenoid states: {cylinders.get_solenoid_states()}")
            print(f"Safe state: {cylinders.is_safe_state()}")
            
            # Test default duration (auto timeout)
            print("\n--- Testing Default Duration ---")
            
            print("Testing extend with default duration (should be quick for testing)...")
            # Use shorter timeout for testing
            success = cylinders.extend(auto_timeout=1.0)
            print(f"Default extend: {'✓' if success else '✗'}")
            print(f"Final cylinder state: {cylinders.get_state()}")
            print(f"Final safe state: {cylinders.is_safe_state()}")
            
            print("\n✓ Cylinders controller test completed successfully")
            
    except Exception as e:
        print(f"✗ Cylinders controller test failed: {e}")
        exit(1) 