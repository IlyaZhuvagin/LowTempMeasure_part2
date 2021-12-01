# -*- coding: UTF-8 -*-

# Use this module to control the Cryogenic Measurement System Software from Python 2.7.
# Example python script to use this:
# import MSS_Control as MSS
# import time
#
# tempA = MSS.get_temperature_A()
# for SPtempA in range(4,10):
#     MSS.set_temperature(SPtempA, 0.1)
#     time.sleep(5)
#     while (MSS.get_temperature_stability_A() == False):
#         time.sleep(5)

import socket
import struct

def open_connection():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', 8089)
    client.connect(server_address)
    return client

def read_data(client):
    size = struct.unpack('i', client.recv(4))[0]  # Extract the msg size from four bytes - mind the encoding
    bytes_data = client.recv(size)
    string_data = bytes_data.decode('ascii')
    if string_data.find('\r\n',len(string_data)-2) >= 0:
        string_data = string_data[0:len(string_data)-2]
    return string_data

def set_field(target_T, ramp_rate_Tpm):
    client = open_connection()
    str_message = 'SET B' + str(target_T) + ',' + str(ramp_rate_Tpm) + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    client.close()

def set_temperature(target_K, ramp_rate_Kpm):
    client = open_connection()
    str_message = 'SET T' + str(target_K) + ',' + str(ramp_rate_Kpm) + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    client.close()

def set_low_current_switch(on_bollean):
    client = open_connection()
    str_message = 'SET LCS' + str(int(on_boolean)) + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    client.close()

def set_persistent_mode_switch(on_boolean):
    client = open_connection()
    str_message = 'SET PERSISTENT_SWITCH' + str(int(on_boolean)) + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    client.close()


def stop_field_ramp():
    client = open_connection()
    str_message = 'STOP B' + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    client.close()

def get_temperature_A():
    client = open_connection()
    client.sendall(b'READ? TA\r\n')
    reply = read_data(client)
#    print(reply)
    split_string = reply.split(',')
    client.close()
    return [float(split_string[0]),float(split_string[1])]

def get_temperature_B():
    client = open_connection()
    client.sendall(b'READ? TB\r\n')
    reply = read_data(client)
#    print(reply)
    split_string = reply.split(',')
    client.close()
    return [float(split_string[0]),float(split_string[1])]

def get_temperature_stability_A():
    client = open_connection()
    client.sendall(b'STAB? TA\r\n')
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def get_temperature_stability_B():
    client = open_connection()
    client.sendall(b'STAB? TB\r\n')
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def get_SMS_output():
    client = open_connection()
    client.sendall(b'READ? BD\r\n')
    split_string = read_data(client).split(',')
    client.close()
    return [float(split_string[0]),float(split_string[1])]

def get_platform_signal():
    client = open_connection()
    client.sendall(b'READ? BA\r\n')
    split_string = read_data(client).split(',')
    client.close()
    return [float(split_string[0]),float(split_string[1])]

def get_ramp_rate():
    # Rate is given in tesla per minute
    client = open_connection()
    client.sendall(b'READ? B RATE\r\n')
    response = read_data(client)
    client.close()
    return [float(response)]

def get_SMS_ramp_status():
    client = open_connection()
    client.sendall(b'STAB? B\r\n')
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def get_low_current_switch():
    client = open_connection()
    client.sendall(b'READ? LCS\r\n')
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def get_persistent_mode_switch():
    client = open_connection()
    client.sendall(b'READ? PERSISTENT_SWITCH\r\n')
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def get_persistent_mode():
    client = open_connection()
    client.sendall(b'READ? PERSISTENT_MODE\r\n')
    out = (read_data(client) == 'TRUE');
    client.close()
    return out


def start_rotation(target_deg, rate_dpm):
    client = open_connection()
    str_message = 'ROTATORSET' + str(target_deg) + ',' + str(rate_dpm) + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def stop_rotation():
    client = open_connection()
    str_message = 'ROTATORSTOP' + '\r\n'
    bytes_message = bytearray(str_message,'ascii')
    client.sendall(bytes_message)
    out = (read_data(client) == 'TRUE');
    client.close()
    return out

def get_angle():
    client = open_connection()
    client.sendall(b'ROTATORPOSITION\r\n')
    reply = read_data(client)
#    print(reply)
    split_string = reply .split(',')
    client.close()
    return [float(split_string[0]),float(split_string[1])]

def get_rotator_status():
    client = open_connection()
    client.sendall(b'ROTATORSTATUS\r\n')
    reply = read_data(client)
#    print(reply)
    client.close()
    return reply
