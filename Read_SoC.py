import serial
import serial.tools.list_ports
import time
import winsound
from datetime import datetime
import keyboard
import threading

# Setup variables and lists
min_charged_voltage = 12.4 # Battery voltage reaches 12.4V when fully charged
min_cell_charged_voltage = 4.15 * 1000 # Single cells reaches 4150mV when fully charged
max_SoC_difference = 0.05 # (SoC-abs_SoC)/SoC <= 5%
max_delta_charged = 10 # Allowance cells delta(mV) when fully charged
max_delta = 100 # Maximum cells delta(mV)
defective_list = []
com_port_list = []

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

    ser.write(bytes.fromhex('A101E60301004000')) # Command for battery voltage
    voltage = ser.read(64)

    ser.write(bytes.fromhex('A101EF0301004000'))
    cell_voltage = ser.read(64)

    return soc, abs_soc, sn, voltage, cell_voltage


# Function to monitor and update SOC
def monitor_soc():
    last_com_port = None

    print('To start: Connect cable to the green type-c port on battery\n')
    print('Hint: Press "i" to see test info\n')

    while True:
        com_port = detect_serial_port()

        if com_port == last_com_port:
            time.sleep(3)

        if com_port:
            last_com_port = com_port

            try:
                with serial.Serial(com_port, baudrate=115200, timeout=1) as ser:
                    soc, abs_soc, sn, voltage, cell_voltage = get_info(ser)

                    if not all([soc, abs_soc, sn, voltage, cell_voltage]):
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
                    SoC_difference = abs((SoC - abs_SoC) / SoC)
                    voltage = int.from_bytes((bytes.fromhex((voltage.hex())[36:40])[::-1]),byteorder='big') / 1000
                    cell_voltage_1 = int.from_bytes((bytes.fromhex((cell_voltage.hex())[2:6])[::-1]),byteorder='big')
                    cell_voltage_2 = int.from_bytes((bytes.fromhex((cell_voltage.hex())[6:10])[::-1]),byteorder='big')
                    cell_voltage_3 = int.from_bytes((bytes.fromhex((cell_voltage.hex())[10:14])[::-1]),byteorder='big')
                    voltage_delta = max(cell_voltage_1, cell_voltage_2, cell_voltage_3) - min(cell_voltage_1, cell_voltage_2, cell_voltage_3)

                    # Evaluate and print status
                    current_time = datetime.now().strftime("%H:%M:%S")

                    def template_pass():
                        print(f'{current_time}[{index}]')
                        print(f'SN: {serial_number}')
                        print(f"SoC(Abs_SoC): {SoC}% ({abs_SoC}%)\n")
                        winsound.Beep(800, 800)

                        # Remove from defective list if apply
                        if serial_number in [item[0] for item in defective_list]:
                            defective_list[:] = [item for item in defective_list if item[0] != serial_number]

                    def template_fail():
                        print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
                        print(f'{current_time}[{index}]')
                        print(f'SN: {serial_number}')
                        print(f"SoC(Abs_SoC): {SoC}% ({abs_SoC}%)")
                        print(f'Voltage: {voltage}V')
                        print(f'Voltage Delta: {voltage_delta}mV')
                        print(f'Symptom: {symptom}')
                        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>> \n')
                        winsound.Beep(2000, 200)
                        winsound.Beep(2000, 200)

                        # Log defective
                        if serial_number not in [item[0] for item in defective_list]:
                            defective_list.append([serial_number, symptom])

                    # When battery is fully charged
                    if 99 <= SoC <= 100 or max(cell_voltage_1, cell_voltage_2, cell_voltage_3) >= min_cell_charged_voltage:
                        if SoC_difference <= max_SoC_difference and voltage_delta <= max_delta_charged and voltage >= min_charged_voltage:
                            template_pass()

                        else:
                            if voltage < min_charged_voltage:
                                symptom = 'Abnormal Voltage'

                            if SoC_difference > max_SoC_difference:
                                symptom = 'Abnormal Abs_SoC'

                            if voltage_delta > max_delta_charged:
                                symptom = f'Imbalanced Cells Voltage: {cell_voltage_1}mV/ {cell_voltage_2}mV/ {cell_voltage_3}mV'

                            template_fail()

                   # When battery is under charged
                    elif SoC < 99:
                       if SoC_difference <= max_SoC_difference and voltage_delta <= max_delta:
                           template_pass()

                       else:
                        if SoC_difference > max_SoC_difference:
                            symptom = 'Abnormal Abs_SoC'

                        if voltage_delta > max_delta:
                            symptom = f'Imbalanced Cells Voltage: {cell_voltage_1}mV/ {cell_voltage_2}mV/ {cell_voltage_3}mV'

                        template_fail()


                    time.sleep(1)

            except serial.SerialException:
                continue  # Ignore and retry


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