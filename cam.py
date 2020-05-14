import time
import board
import busio
import adafruit_mlx90640
import base64
import numpy as np

import datetime

#dir(adafruit_mlx90640.RefreshRate)
#['REFRESH_0_5_HZ', 'REFRESH_16_HZ', 'REFRESH_1_HZ', 'REFRESH_2_HZ', 'REFRESH_32_HZ', 'REFRESH_4_HZ', 'REFRESH_64_HZ', 'REFRESH_8_HZ', 
# '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__']

frame_rates={
    'a':adafruit_mlx90640.RefreshRate.REFRESH_0_5_HZ,
    'b':adafruit_mlx90640.RefreshRate.REFRESH_1_HZ,
    'c':adafruit_mlx90640.RefreshRate.REFRESH_2_HZ,
    'd':adafruit_mlx90640.RefreshRate.REFRESH_4_HZ,
    'e':adafruit_mlx90640.RefreshRate.REFRESH_8_HZ,
    'f':adafruit_mlx90640.RefreshRate.REFRESH_16_HZ,
    'g':adafruit_mlx90640.RefreshRate.REFRESH_32_HZ,
    'h':adafruit_mlx90640.RefreshRate.REFRESH_64_HZ,
    }

# Startup
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)

mlx = adafruit_mlx90640.MLX90640(i2c)
print("MLX addr detected on I2C", [hex(i) for i in mlx.serial_number])

mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
rawFrame=[0]*768
while True:
    z=input()
    if z=='q':
        break
    if z in frame_rates:
        mlx.refresh_rate=frame_rates[z]
    try:
        mlx.getFrame(rawFrame)
        encoded=base64.b64encode(np.array(rawFrame).astype(np.float32).tobytes()).decode()
        print(len(encoded),encoded,'END')
        #img=np.array(self.rawFrame).reshape((24,32))
        #print( time.time(), (" ".join(["%3.1f"]*10))%tuple(rawFrame[:10]))
    except ValueError:
        pass
    #except:
    #    print("Failed to get frame")
    #    break

