#!/usr/bin/env python3
"""
Test script to verify GUI display functionality on touchscreen.
Creates a simple window to confirm display and touch interaction work.
"""

import tkinter as tk
from tkinter import ttk
import sys
import platform
from datetime import datetime

class GUITest:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.create_widgets()
        
    def setup_window(self):
        """Configure the main window."""
        self.root.title("EOL Leak Tester - GUI Test")
        self.root.geometry("800x480")  # Common touchscreen resolution
        
        # Make window fullscreen on Pi, windowed on development machine
        if self.is_raspberry_pi():
            self.root.attributes('-fullscreen', True)
            self.root.configure(cursor='none')  # Hide cursor for touchscreen
        
        self.root.configure(bg='#2c3e50')
        
    def is_raspberry_pi(self):
        """Detect if running on a Raspberry Pi."""
        machine = platform.machine().lower()
        release = platform.release().lower()
        platform_str = platform.platform().lower()
        
        is_arm = machine.startswith('arm') or machine.startswith('aarch64')
        is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
        
        return platform.system() == "Linux" and (is_arm or is_rpi_kernel)
        
    def create_widgets(self):
        """Create and layout GUI widgets."""
        # Main title
        title_label = tk.Label(
            self.root,
            text="EOL Leak Tester",
            font=('Arial', 32, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(pady=40)
        
        # Status display
        status_frame = tk.Frame(self.root, bg='#2c3e50')
        status_frame.pack(pady=20)
        
        tk.Label(
            status_frame,
            text="GUI Test Status:",
            font=('Arial', 18, 'bold'),
            fg='white',
            bg='#2c3e50'
        ).pack()
        
        self.status_label = tk.Label(
            status_frame,
            text="✓ Display Working",
            font=('Arial', 16),
            fg='#27ae60',
            bg='#2c3e50'
        )
        self.status_label.pack(pady=10)
        
        # Platform info
        info_frame = tk.Frame(self.root, bg='#2c3e50')
        info_frame.pack(pady=20)
        
        platform_text = f"Platform: {platform.system()} {platform.release()}\nMachine: {platform.machine()}"
        tk.Label(
            info_frame,
            text=platform_text,
            font=('Arial', 12),
            fg='#bdc3c7',
            bg='#2c3e50',
            justify='left'
        ).pack()
        
        # Touch test button
        self.touch_test_button = tk.Button(
            self.root,
            text="Touch Test\n(Click Me)",
            font=('Arial', 18, 'bold'),
            width=15,
            height=3,
            bg='#3498db',
            fg='white',
            activebackground='#2980b9',
            activeforeground='white',
            relief='raised',
            bd=3,
            command=self.on_touch_test
        )
        self.touch_test_button.pack(pady=30)
        
        # Touch counter
        self.touch_count = 0
        self.touch_counter_label = tk.Label(
            self.root,
            text=f"Touches: {self.touch_count}",
            font=('Arial', 14),
            fg='white',
            bg='#2c3e50'
        )
        self.touch_counter_label.pack(pady=10)
        
        # Exit button
        exit_button = tk.Button(
            self.root,
            text="Exit Test",
            font=('Arial', 14),
            width=10,
            height=2,
            bg='#e74c3c',
            fg='white',
            activebackground='#c0392b',
            activeforeground='white',
            command=self.exit_app
        )
        exit_button.pack(side='bottom', pady=20)
        
        # Bind ESC key to exit (for development)
        self.root.bind('<Escape>', lambda e: self.exit_app())
        
    def on_touch_test(self):
        """Handle touch test button press."""
        self.touch_count += 1
        self.touch_counter_label.config(text=f"Touches: {self.touch_count}")
        
        # Update status
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(
            text=f"✓ Touch Working - Last: {timestamp}",
            fg='#27ae60'
        )
        
        # Visual feedback
        self.touch_test_button.config(bg='#27ae60')
        self.root.after(200, lambda: self.touch_test_button.config(bg='#3498db'))
        
    def exit_app(self):
        """Exit the application."""
        print(f"GUI test completed. Total touches: {self.touch_count}")
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """Start the GUI application."""
        print("=== GUI Display Test ===")
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Machine: {platform.machine()}")
        print(f"Raspberry Pi: {'Yes' if self.is_raspberry_pi() else 'No'}")
        print("Starting GUI... (Press ESC or click Exit to close)")
        
        try:
            self.root.mainloop()
            return True
        except Exception as e:
            print(f"✗ GUI test failed: {e}")
            return False

def main():
    """Main entry point."""
    try:
        gui_test = GUITest()
        success = gui_test.run()
        return 0 if success else 1
    except ImportError as e:
        print(f"✗ GUI libraries not available: {e}")
        print("  tkinter should be included with Python")
        return 1
    except Exception as e:
        print(f"✗ GUI test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 