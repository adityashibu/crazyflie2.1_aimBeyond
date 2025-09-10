import cflib.crtp
import time
import threading
import sys

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

# Trim values to compensate for drift
TRIM_ROLL = 0.0    # Adjust if drifting left(-) or right(+)
TRIM_PITCH = 0.0   # Adjust if drifting backward(-) or forward(+)

# Control variables
control_active = False
thrust = 0
roll = 0
pitch = 0
yaw = 0

# Base thrust and control sensitivity
BASE_THRUST = 10000
THRUST_INCREMENT = 2000
MAX_THRUST = 50000
MIN_THRUST = 10000
CONTROL_SENSITIVITY = 5.0

URI = 'radio://0/80/2M'

def keyboard_listener():
    """Simple keyboard input handler - works on Linux/Mac"""
    global control_active, thrust, roll, pitch, yaw
    
    print("\n=== DRONE CONTROLS ===")
    print("W/S: Forward/Backward")
    print("A/D: Left/Right") 
    print("Space: Increase thrust")
    print("Z: Decrease thrust")  # Changed from Shift to Z
    print("Q: Emergency stop")
    print("E: Exit")
    print("======================\n")
    
    try:
        import termios, tty
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
        while control_active:
            ch = sys.stdin.read(1)
            
            if ch.lower() == 'w':  # Forward
                pitch = -CONTROL_SENSITIVITY
            elif ch.lower() == 's':  # Backward  
                pitch = CONTROL_SENSITIVITY
            elif ch.lower() == 'a':  # Left
                roll = -CONTROL_SENSITIVITY
            elif ch.lower() == 'd':  # Right
                roll = CONTROL_SENSITIVITY
            elif ch == ' ':  # Space - increase thrust
                thrust = min(thrust + THRUST_INCREMENT, MAX_THRUST)
                print(f"Thrust: {thrust}")
            elif ch.lower() == 'z':  # Z key - decrease thrust
                thrust = max(thrust - THRUST_INCREMENT, MIN_THRUST)
                print(f"Thrust: {thrust}")
            elif ch.lower() == 'q':  # Emergency stop
                thrust = 0
                roll = pitch = yaw = 0
                print("EMERGENCY STOP!")
            elif ch.lower() == 'e':  # Exit
                control_active = False
                print("Exiting...")
                break
                
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
    except ImportError:
        # Fallback for systems without termios (Windows)
        print("Termios not available. Using basic input...")
        while control_active:
            key = input("Enter command (w/a/s/d/space/z/q/e): ").lower()
            if key == 'w':
                pitch = -CONTROL_SENSITIVITY
            elif key == 's':
                pitch = CONTROL_SENSITIVITY
            elif key == 'a':
                roll = -CONTROL_SENSITIVITY
            elif key == 'd':
                roll = CONTROL_SENSITIVITY
            elif key == 'space':
                thrust = min(thrust + THRUST_INCREMENT, MAX_THRUST)
            elif key == 'z':  # Changed to 'z' key
                thrust = max(thrust - THRUST_INCREMENT, MIN_THRUST)
            elif key == 'q':
                thrust = 0
                roll = pitch = yaw = 0
            elif key == 'e':
                control_active = False
                break 

def control_loop(scf):
    """Main control loop that sends commands to drone"""
    global control_active, thrust, roll, pitch, yaw
    
    print("Starting manual control mode...")
    control_active = True
    thrust = BASE_THRUST
    
    # Start keyboard listener in separate thread
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    try:
        while control_active:
            # Apply trim and send setpoint
            final_roll = roll + TRIM_ROLL
            final_pitch = pitch + TRIM_PITCH
            
            scf.cf.commander.send_setpoint(final_roll, final_pitch, yaw, thrust)
            
            # Reset control values (so drone stops when key is released)
            roll = pitch = yaw = 0
            
            time.sleep(0.05)  # 20Hz control loop
            
    except KeyboardInterrupt:
        print("\nKeyboard interrupt - landing...")
    finally:
        control_active = False
        # Land the drone
        for land_thrust in range(thrust, 0, -1000):
            scf.cf.commander.send_setpoint(TRIM_ROLL, TRIM_PITCH, 0, max(land_thrust, 0))
            time.sleep(0.1)
        scf.cf.commander.send_stop_setpoint()

# Main execution
cflib.crtp.init_drivers()

with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
    print("Connected to Crazyflie!")
    
    print("Arming motors...")
    for _ in range(10):
        scf.cf.platform.send_arming_request(True)
        scf.cf.commander.send_setpoint(0, 0, 0, 0)
        time.sleep(0.05)
    
    print("Starting propellers...")
    for _ in range(50):
        scf.cf.commander.send_setpoint(TRIM_ROLL, TRIM_PITCH, 0, BASE_THRUST)
        time.sleep(0.02)
    
    # Enter manual control mode
    control_loop(scf)
    
    print("Propellers stopped.")
    scf.cf.platform.send_arming_request(False)
    time.sleep(0.5)
