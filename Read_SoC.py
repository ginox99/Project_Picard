import serial
import serial.tools.list_ports
import time
import winsound
from datetime import datetime
import keyboard
import threading

# Function to detect available serial ports
def detect_serial_port():
    ports = list(serial.tools.list_ports.comports())
    if len(ports) == 0:
        return None  # Return None if no serial devices are found

    # Default to use the first available COM port
    return ports[0].device


# Function to read SOC
def get_info(ser):
    ser.write(bytes.fromhex('A101E00301004000'))  # Command for SOC
    soc = ser.read(64)  # Read the response for SOC

    ser.write(bytes.fromhex('A101ED0301004000'))  # Command for abs_SOC
    abs_soc = ser.read(64)  # Read the response for abs_SOC

    ser.write(bytes.fromhex('A101D30301004000')) # Command for serial number
    sn = ser.read(64) # Read the response for serial number

    return soc, abs_soc, sn

defective_list = []
com_port_list = []

# Function to monitor and update SOC
def monitor_soc():
    last_com_port = None

    print('To start: Connect cable to the green type-c port on battery\n')
    print('Hint: Press "i" to see test info\n')

    while True:
        com_port = detect_serial_port()

        if com_port:
            last_com_port = com_port

            try:
                with serial.Serial(com_port, baudrate=115200, timeout=1) as ser:
                    soc, abs_soc, sn = get_info(ser)

                    if not all([soc, abs_soc, sn]):
                        print("Reading failed.")
                        continue

                    # Track COM ports
                    if com_port not in com_port_list:
                        com_port_list.append(com_port)

                    index = com_port_list.index(com_port) + 1

                    # Decode values
                    serial_number = bytes.fromhex(sn.hex()[12:42]).decode('ascii')
                    SoC = int(soc.hex()[2:4], 16)
                    abs_SoC = int(abs_soc.hex()[2:4], 16)

                    # Evaluate and print status
                    current_time = datetime.now().strftime("%H:%M:%S")

                    if SoC >= 99 and 95 <= abs_SoC <= 105:
                        print(f'{current_time}[{index}]')
                        print(f'SN: {serial_number}')
                        print(f"SoC(Abs_SoC): {SoC}% ({abs_SoC}%)\n")
                        winsound.Beep(800, 800)
                        if serial_number in [item[0] for item in defective_list]:
                            defective_list[:] = [item for item in defective_list if item[0] != serial_number]
                    else:
                        print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
                        print(f'{current_time}[{index}]')
                        print(f'SN: {serial_number}')
                        print(f"SoC(Abs_SoC): {SoC}% ({abs_SoC}%)")
                        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>> \n')
                        winsound.Beep(2000, 200)
                        winsound.Beep(2000, 200)

                        # Determine issue
                        symptom = []
                        if SoC < 99:
                            symptom.append('Under Charged')
                        if abs_SoC < 95:
                            symptom.append('Low ABS SoC')
                        if abs_SoC > 105:
                            symptom.append('High ABS SoC')
                        else:
                            symptom.append('Unknown')

                        # Log defective
                        if serial_number not in [item[0] for item in defective_list]:
                            defective_list.append([serial_number, symptom])

                    time.sleep(1)

            except serial.SerialException:
                continue  # Ignore and retry

        time.sleep(2)


# Keyboard input detection in a separate thread
def listen_for_keypress():
    while True:
        if keyboard.is_pressed('i'):
            print(f'Tested units:{len(com_port_list)}')
            print(f'Problem units:{len(defective_list)} ')

            if len(defective_list) > 0:
                for i in range(len(defective_list)):
                    print(f'SN: {defective_list[i][0]}  Symptom: {defective_list[i][1]}')
            print(' \n')
            time.sleep(0.5)


# Start keypress listener in a separate thread
key_thread = threading.Thread(target=listen_for_keypress, daemon=True)
key_thread.start()

# Start monitoring SOC (this blocks the main thread)
monitor_soc()