import time


import matplotlib.pyplot as plt
import cv2
import numpy as np
import datetime
import serial
import base64


class ThermalCameraReader:
    def __init__(self,port):
        if port != 'Simulation':
            # configure the serial connections 
            self.ser = serial.Serial(
                port=port,
                baudrate=115200,
                timeout=1
                #parity=serial.PARITY_ODD,
                #stopbits=serial.STOPBITS_TWO,
                #bytesize=serial.SEVENBITS
            )

            self.ser.isOpen()
        else:
            self.ticker=0
            self.ser=None
    def get_frame(self):
        if self.ser:
            self.ser.write(('\n').encode())
            back=self.ser.readline().strip()
            if len(back)<50:
                back=self.ser.readline().strip()
            #print(back)
            if len(back)<50:
                return None
            z=back.split()
            if z[-1] != b'END':
                print(z[-1])
                return None
            try:
                q=base64.b64decode(z[-2])
            except:
                print("Failed decode")
                return None
            print(len(q))
            img=np.frombuffer(q,dtype=np.float32)
            print(len(img))
            img=img.reshape((24,32))
            img=np.fliplr(img)
            return img
        else:
            time.sleep(0.3)
            x,y=np.meshgrid(np.linspace(-1,1,32),np.linspace(-1,1,24))
            assert(x.shape==(24,32))
            img=np.cos(x+self.ticker/50.)*np.sin(y+self.ticker/30) *20.+10
            self.ticker+=1
            return img


maxtemp=30
mintemp=10

#https://stackoverflow.com/questions/52498777/apply-matplotlib-or-custom-colormap-to-opencv-image

def apply_custom_colormap(image_gray, cmap=plt.get_cmap('seismic')):

    assert image_gray.dtype == np.uint8, 'must be np.uint8 image'
    if image_gray.ndim == 3: image_gray = image_gray.squeeze(-1)

    # Initialize the matplotlib color map
    sm = plt.cm.ScalarMappable(cmap=cmap)

    # Obtain linear color range
    color_range = sm.to_rgba(np.linspace(0, 1, 256))[:,0:3]    # color range RGBA => RGB
    color_range = (color_range*255.0).astype(np.uint8)         # [0,1] => [0,255]
    color_range = np.squeeze(np.dstack([color_range[:,2], color_range[:,1], color_range[:,0]]), 0)  # RGB => BGR

    # Apply colormap for each channel individually
    channels = [cv2.LUT(image_gray, color_range[:,i]) for i in range(3)]
    return np.dstack(channels)



class OpenCVApp:
    def __init__(self,windowTitle="Someone forgot to set a window title",port="Simulation",delay=3):
        self.windowTitle=windowTitle
        self.camera=ThermalCameraReader(port)
        self.delay=int(delay)
        self.fps=0.
        self.frameTimes=[0.]*10
        self.frameTimesSum=0.
        self.frameTimesIndex=0
        self.rawFrame = [0] * 768
        self.recording=False
        self.prefix=time.strftime('%H%M%S')
        pass

    def compute_fps(self):
        now=time.time()
        deltaTime=now-self.lastTime
        self.frameTimesSum-=self.frameTimes[self.frameTimesIndex]
        self.frameTimes[self.frameTimesIndex]=deltaTime
        self.frameTimesSum+=self.frameTimes[self.frameTimesIndex]
        self.frameTimesIndex=(self.frameTimesIndex+1)%len(self.frameTimes)
        self.lastTime=now
        self.fps=len(self.frameTimes)/self.frameTimesSum
 
    def on_key(self,key):
        if key != -1 and key != 255:
            if key==27:
                return False
            if key==114:
                self.recording= not self.recording
                if self.recording:
                   print("Recording on")
                   self.prefix=time.strftime('%H%M%S')
                   self.framecount=0
                else:
                   print("Recording off")

            else:
                print("OpenCVApp: The key was",key)
                
        return True
    

    def overlay(self,frame):
        resultFrame=frame.copy()
        cv2.putText(resultFrame,"FPS: %3.1f"%(self.fps),
                    (int(resultFrame.shape[1]*0.8), int(resultFrame.shape[0]*0.05)),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,0,255))
        return resultFrame

    def run(self):
        cv2.namedWindow(self.windowTitle)
        loop = True
        self.lastTime=time.time()
        while(loop):
            while True:
                try:
                    #img=np.random.rand(24,32)
                    #print("Got one")
                    img=self.camera.get_frame()
                    img=np.clip(np.round((img-mintemp)/(maxtemp-mintemp) * 255),0,255).astype(np.uint8)
                    img=apply_custom_colormap(img)
                    img=cv2.resize(img,(240,320))
                    self.processedFrame=np.pad(img,((64,64),(64,64),(0,0)),'constant')
                    self.overlayFrame=self.overlay(self.processedFrame)
                    cv2.imshow(self.windowTitle,self.overlayFrame)
                    if self.recording:
                        cv2.imwrite(self.prefix+"_%05d.png"%self.framecount,self.overlayFrame)
                        self.framecount+=1
            
                    self.compute_fps()
                    break
                except ValueError:
                    # these happen, no biggie - retry
                    pass #continue
                    break
            char = cv2.waitKey(self.delay)
            loop=self.on_key(char)
            
        cv2.destroyWindow(self.windowTitle)

    


if __name__ == '__main__':
    # simple test here.
    App=OpenCVApp("Test OpenCVApp",delay=500,port='/dev/ttyUSB0')
    App.run()

#   LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1 




#
#    for h in range(24):
#        for w in range(32):
#            t = frame[h*32 + w]
#            print("%0.1f, " % t, end="")
#        print()
#    print()
