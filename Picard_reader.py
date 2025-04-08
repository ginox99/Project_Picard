import serial
import serial.tools.list_ports
import time


# Function to detect available serial ports
def detect_serial_port():
    ports = list(serial.tools.list_ports.comports())
    if len(ports) == 0:
        return None  # Return None if no serial devices are found

    # Default to use the first available COM port
    return ports[0].device


# Function to read SOC
def get_info(ser):
    # Dictionary of commands
    command_dict = {
        'SoC': 'A101E00301004000',
        'abs_SoC':'A101ED0301004000',
        'sn_num': 'A101D30301004000',
        'hardware_ver': 'A101D40301004000',
        'bootLoader_ver': 'A101D50301004000',
        'firmware_ver': 'A101D60301004000',
        'pd_output': 'A101C40301004000',
        'temperature': 'A101E10301004000',
        'health': 'A101E40301004000',
        'design_capacity': 'A101EB0301004000',
        'actual_capacity': 'A101EC0301004000',
        'remain_capacity': 'A101EE0301004000',
        'voltage': 'A101EF0301004000',

    }
    # Dictionary of response value
    response_dict = {
        'SoC': '',
        'abs_SoC': '',
        'sn_num': '',
        'hardware_ver': '',
        'bootLoader_ver': '',
        'firmware_ver': '',
        'pd_output': '',
        'temperature': '',
        'health': '',
        'design_capacity': '',
        'actual_capacity':'',
        'remain_capacity': '',
        'voltage': '',
    }

    # Send commands to battery
    for key1, value1 in command_dict.items():
        command = bytes.fromhex(command_dict[key1])
        ser.write(command)
        # Read response from the battery
        response = ser.read(128)
        #print(command_dict[key1], response.hex())
        if key1 in response_dict:
            response_dict[key1] = response.hex()

    return response_dict


# Function to monitor and update SOC
def monitor_info():
    last_com_port = None

    while True:
        # Detect the serial port
        com_port = detect_serial_port()

        if com_port is None:
            #print("No serial devices found.")
            continue

        if com_port is not None:
            last_com_port = com_port
            try:
                # Setup serial connection with the detected COM port
                ser = serial.Serial(com_port, baudrate=115200, timeout=1)

                print('Reading info....\n')
                info = get_info(ser)

                SoC = int((info['SoC'])[2:4],16)
                abs_Soc = int((info['abs_SoC'])[2:4],16)
                sn_num = bytes.fromhex((info['sn_num'])[12:42]).decode('ascii')
                hardware_ver = bytes.fromhex((info['hardware_ver'])[4:10]).decode('ascii')
                bootLoader_ver = bytes.fromhex((info['bootLoader_ver'])[14:24]).decode('ascii')
                firmware_ver = bytes.fromhex((info['firmware_ver'])[24:34]).decode('ascii')
                temperature = int.from_bytes((bytes.fromhex((info['temperature'])[2:10])[::-1]),byteorder='big')
                health = int.from_bytes((bytes.fromhex((info['health'])[2:6])[::-1]),byteorder='big')
                design_capacity = int.from_bytes((bytes.fromhex((info['design_capacity'])[2:6])[::-1]),byteorder='big')
                actual_capacity = int.from_bytes((bytes.fromhex((info['actual_capacity'])[2:6])[::-1]),byteorder='big')
                remain_capacity = int.from_bytes((bytes.fromhex((info['remain_capacity'])[2:6])[::-1]),byteorder='big')
                voltage_1 = int.from_bytes((bytes.fromhex((info['voltage'])[2:6])[::-1]),byteorder='big')
                voltage_2 = int.from_bytes((bytes.fromhex((info['voltage'])[6:10])[::-1]),byteorder='big')
                voltage_3 = int.from_bytes((bytes.fromhex((info['voltage'])[10:14])[::-1]),byteorder='big')

                if (info['pd_output'])[32:40] == 'ffffffff' or (info['pd_output'])[40:48] == 'ffffffff':
                    pd_voltage = 0
                    pd_current = 0
                else:
                    pd_voltage = int.from_bytes((bytes.fromhex((info['pd_output'])[32:40])[::-1]),byteorder='big')
                    pd_current = int.from_bytes((bytes.fromhex((info['pd_output'])[40:48])[::-1]),byteorder='big')


                if info is not None and len(info) == 13:
                    # Print the info value if it's valid
                    print(f"COM Port: {com_port}")
                    print(f'SoC(Abs_SoC): {SoC}%({abs_Soc}%)')
                    print(f'SN number: {sn_num}')
                    print(f'Hardware version: {hardware_ver}')
                    print(f'Boot Loader version: {bootLoader_ver}')
                    print(f'Firmware version: {firmware_ver}')
                    print(f'Battery Voltage: {voltage_1 + voltage_2 + voltage_3}mV')
                    print(f'Cells voltage: {voltage_1}mV/{voltage_2}mV/{voltage_3}mV')
                    print(f'Voltage delta: {max([voltage_1, voltage_2, voltage_3]) - min([voltage_1,voltage_2,voltage_3])}mV')
                    if pd_voltage != 0 and pd_current != 0:
                        print(f'PD output:\n {pd_voltage}mV\n {pd_current}mA\n {(pd_voltage * pd_current) / (10 ** 6)}W')
                    print(f'Cells Temperature: {temperature / 100}')
                    print(f'Health: {health}')
                    print(f'Design Capacity: {design_capacity}mAh')
                    print(f'Actual Capacity: {actual_capacity}mAh')
                    print(f'Remaining Capacity: {remain_capacity}mAh\n')

                else:
                    print("Info reading failed or invalid responses.")


                # Close the serial connection before detecting port again
                if ser.is_open:
                    ser.close()

            except serial.SerialException as e:

                continue  # Simply continue to next iteration

        time.sleep(10)

# Start monitoring SOC
monitor_info()
