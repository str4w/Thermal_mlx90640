import serial
import base64
import numpy as np

# configure the serial connections 
ser = serial.Serial(
    port='/dev/ttyUSB1',
    baudrate=115200,
    #parity=serial.PARITY_ODD,
    #stopbits=serial.STOPBITS_TWO,
    #bytesize=serial.SEVENBITS
)

ser.isOpen()

print('Enter your commands below.\nInsert "q" to leave the application.')

while True:
    # get keyboard input
    z=input("::")
    if z=="q":
        break
    else:
        ser.write((z+'\n').encode())
        back=ser.readline().strip()
        if len(back)>10:
            darray=back.split()
            data=darray[-2]
            #z=np.frombuffer(base64.b64decode(data))
            print("Got",len(data),len(darray),darray[-1],data[:10])
            if darray[-1] == b'END':
               z=np.frombuffer(base64.b64decode(data))
