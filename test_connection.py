import cflib.crtp
import time

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

# Trim values to compensate for drift (adjust these based on your drone's behavior)
TRIM_ROLL = 0.0    # Adjust if drifting left(-) or right(+)
TRIM_PITCH = 0.0   # Adjust if drifting backward(-) or forward(+)

URI = 'radio://0/80/2M'

cflib.crtp.init_drivers()

with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
    print("Connected to Crazyflie!")

    print("Arming motors...")
    for _ in range(10):
        scf.cf.platform.send_arming_request(True)
        scf.cf.commander.send_setpoint(0, 0, 0, 0)
        time.sleep(0.05)

    print("Starting propellers (minimum thrust)...")
    for _ in range(100):
        scf.cf.commander.send_setpoint(TRIM_ROLL, TRIM_PITCH, 0, 10000)
        time.sleep(0.01)

    print("Taking off to moderate altitude...")
    for _ in range(250):
        scf.cf.commander.send_setpoint(TRIM_ROLL, TRIM_PITCH, 0, 37500)
        time.sleep(0.01)

    print("Hovering at altitude...")
    for _ in range(200):
        scf.cf.commander.send_setpoint(TRIM_ROLL, TRIM_PITCH, 0, 36000)
        time.sleep(0.01)

    print("Landing...")
    for thrust in range(35000, 10000, -500):
        scf.cf.commander.send_setpoint(TRIM_ROLL, TRIM_PITCH, 0, thrust)
        time.sleep(0.05)

    scf.cf.commander.send_stop_setpoint()
    print("Propellers stopped.")

    scf.cf.platform.send_arming_request(False)
    time.sleep(0.5)
