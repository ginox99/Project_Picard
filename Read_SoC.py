import serial
import serial.tools.list_ports
import time
import winsound
from datetime import datetime

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


# Function to monitor and update SOC
def monitor_soc():
    last_com_port = None
    com_port_list = []

    if last_com_port is None:
        print('Please connect cable to the green type-c port on battery\n')

    while True:
        # Detect the serial port
        com_port = detect_serial_port()

        if com_port is not None:
            last_com_port = com_port

            try:
                # Setup serial connection with the detected COM port
                ser = serial.Serial(com_port, baudrate=115200, timeout=1)
                soc, abs_soc, sn = get_info(ser)

                # Check if the port is already in the list
                if com_port not in com_port_list:
                    com_port_list.append(com_port)

                index = com_port_list.index(com_port) + 1

                # Decode responses
                serial_number = bytes.fromhex((sn.hex())[12:42]).decode('ascii')
                SoC = int((soc.hex())[2:4],16)
                abs_SoC = int((abs_soc.hex())[2:4],16)

                if soc and abs_soc and sn:  # Ensure data is not null
                    if SoC >= 99 and abs_SoC >= 95 and abs_SoC <= 105:
                        current_time = datetime.now().strftime("%H:%M:%S") # Get current time
                        print(f'{current_time}[{index}]')
                        print(f'SN: {serial_number}')
                        print(f"SoC(Abs_SoC): {SoC}% ({abs_SoC}%)\n")
                        winsound.Beep(800, 800)
                    else:
                        current_time = datetime.now().strftime("%H:%M:%S")
                        print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
                        print(f'{current_time}[{index}]')
                        print(f'SN: {serial_number}')
                        print(f"SoC(Abs_SoC): {SoC}% ({abs_SoC}%)")
                        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>> \n')
                        winsound.Beep(2000, 200)
                        winsound.Beep(2000, 200)

                else:
                    print("Reading failed.")

                # Close the serial connection before detecting port again
                if ser.is_open:
                    ser.close()

                # Wait for 1 second before reading again
                time.sleep(1)

            except serial.SerialException as e:
                continue # Simply continue to next iteration

        # Wait for 2 seconds before attempting to detect the port again
        time.sleep(2)


# Start monitoring SOC
monitor_soc()
