import numpy as np
import cv2
import matplotlib.pyplot as plt
import time
import serial,serial.tools.list_ports
import base64
from PIL import Image

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class FakeCamera:
    def __init__(self):
        self.ticker=0
    def getFrame(self):
        #time.sleep(0.3)
        x,y=np.meshgrid(np.linspace(-1,1,32),np.linspace(-1,1,24))
        assert(x.shape==(24,32))
        img=np.cos(x+self.ticker/50.)*np.sin(y+self.ticker/30) *20.+10
        self.ticker+=1
        return img

class ThermalCamera:
    def __init__(self,port):
        # configure the serial connections 
        self.ser = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=5.
            #parity=serial.PARITY_ODD,
            #stopbits=serial.STOPBITS_TWO,
            #bytesize=serial.SEVENBITS
        )

        self.ser.isOpen()
    def getFrame(self):
        self.ser.write(('\n').encode())
        back=self.ser.readline().strip()
        if len(back)<50:
            #print("short",len(back),back)

            back=self.ser.readline().strip()
        #print(len(back),back)
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
        #print(len(q))
        img=np.frombuffer(q,dtype=np.float32)
        #print(len(img))
        img=img.reshape((24,32))
        img=np.fliplr(img)
        return img

DEFAULT_MAX_TEMP=30
DEFAULT_MIN_TEMP=10




#https://stackoverflow.com/questions/52498777/apply-matplotlib-or-custom-colormap-to-opencv-image

def apply_custom_colormap(image_gray, cmap=plt.get_cmap('seismic')):

    assert image_gray.dtype == np.uint8, 'must be np.uint8 image'
    if image_gray.ndim == 3: image_gray = image_gray.squeeze(-1)

    # Initialize the matplotlib color map
    sm = plt.cm.ScalarMappable(cmap=cmap)

    # Obtain linear color range
    color_range = sm.to_rgba(np.linspace(0, 1, 256))[:,0:3]    # color range RGBA => RGB
    color_range = (color_range*255.0).astype(np.uint8)         # [0,1] => [0,255]
    color_range = np.squeeze(np.dstack([color_range[:,0], color_range[:,1], color_range[:,2]]), 0)  # RGB => BGR

    # Apply colormap for each channel individually
    channels = [cv2.LUT(image_gray, color_range[:,i]) for i in range(3)]
    return np.dstack(channels)
class Worker(QThread):

    def __init__(self, parent = None):
    
        QThread.__init__(self, parent)
        self.exiting = False

class CameraThread(QThread):
    statsComputed=Signal(dict)
    def __init__(self,display,parent=None):
        QThread.__init__(self,parent)
        self.display=display
        self.exiting=False
        self.at_point=(0,0)
        try:
            self.camera=ThermalCamera('/dev/ttyUSB1')
        except Exception as e:
            print(e)
            print("Initializing Thermal Camera failed")
            print("Falling back to simulation")
            self.camera=FakeCamera()
        self.maxtemp=5
        self.mintemp=0
        self.draw_at_point=True
        self.interpolation_method=Image.NEAREST
        self.cmap=plt.get_cmap('seismic')
    def set_max_temp(self,t):
        self.maxtemp=t
    def set_min_temp(self,t):
        self.mintemp=t
    def set_interpolation_method(self,m):
        if m=="Nearest":
            self.interpolation_method=Image.NEAREST
        elif m=="Linear":
            self.interpolation_method=Image.BILINEAR
        elif m=="Cubic":
            self.interpolation_method=Image.BICUBIC
        else:
            print("BUG: unknow interpolamt",m)

    def set_cmap(self,cmap_name):
        self.cmap=plt.get_cmap(cmap_name.lower())

    def set_draw_at_point(self,draw):
        self.draw_at_point=draw>0
    def cursor_up(self):
        self.at_point=(max(self.at_point[0]-1,0),self.at_point[1])
    def cursor_down(self):
        self.at_point=(min(self.at_point[0]+1,23),self.at_point[1])
    def cursor_left(self):
        self.at_point=(self.at_point[0],max(self.at_point[1]-1,0))
    def cursor_right(self):
        self.at_point=(self.at_point[0],min(self.at_point[1]+1,31))

    def getFrame(self):
        rawimg=self.camera.getFrame()
        if rawimg is not None:
            img=np.clip(np.round((rawimg-self.mintemp)/(self.maxtemp-self.mintemp) * 255),0,255).astype(np.uint8)
            img=apply_custom_colormap(img,self.cmap)
            img=Image.fromarray(img)    
            img=np.array(img.resize((320,240),self.interpolation_method))
            if self.draw_at_point:
                img[self.at_point[0]*10+5,:,:]=0
                img[:,self.at_point[1]*10+5,:]=0
            #img=(np.random.rand(250,200,3)*256).astype(np.uint8)
            #self.qimg=QImage(img)
            self.qimg=QImage(img,img.shape[1],img.shape[0],QImage.Format_RGB888)
            #self.qimg=QImage(img,img.shape[1],img.shape[0],QImage.Format_RGB888)
            self.qpixmap=QPixmap.fromImage(self.qimg)
            self.display.setPixmap(self.qpixmap)

            stats={
                "max":np.max(rawimg),
                "min":np.min(rawimg),
                "mean":np.mean(rawimg),
                "at_point": rawimg[self.at_point[0],self.at_point[1]]
            }
            self.statsComputed.emit(stats)

    def __del__(self):
        self.exiting = True
        self.wait()
    def run(self):
        while not self.exiting:
            self.getFrame()


class ThermalApp:
    def __init__(self):
        self.app = QApplication([])
        # dark color scheme
        # based on https://gist.github.com/Skyrpex/5547015
        self.app.setStyle("fusion")

        palette=QPalette()
        palette.setColor(QPalette.Window, QColor(53,53,53))
        palette.setColor(QPalette.WindowText, QColor(255,255,255))
        palette.setColor(QPalette.Base, QColor(15,15,15))
        palette.setColor(QPalette.AlternateBase, QColor(53,53,53));
        palette.setColor(QPalette.ToolTipBase, QColor(255,255,255))
        palette.setColor(QPalette.ToolTipText, QColor(255,255,255))
        palette.setColor(QPalette.Text, QColor(255,255,255))
        palette.setColor(QPalette.Button, QColor(53,53,53))
        palette.setColor(QPalette.ButtonText, QColor(255,255,255))
        palette.setColor(QPalette.BrightText, QColor(255,0,0))

        palette.setColor(QPalette.Highlight, QColor(142,45,197).lighter())
        palette.setColor(QPalette.HighlightedText, QColor(0,0,0));

        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(60,60,60))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(60,60,60))
        self.app.setPalette(palette)


#print([comport.device for comport in serial.tools.list_ports.comports()])

        self.window = QWidget()
        self.main_layout = QHBoxLayout()
        self.sidebar = QVBoxLayout()
        self.display = QLabel()
        self.display.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.camera_worker=CameraThread(self.display)
        self.camera_worker.statsComputed[dict].connect(self.stats_callback)
        self.main_layout.addLayout(self.sidebar)
        self.main_layout.addWidget(self.display)

        self.max_temp_layout=QHBoxLayout()
        self.max_temp=QSpinBox()
        self.max_temp.valueChanged[int].connect(self.camera_worker.set_max_temp)
        self.max_temp.setValue(DEFAULT_MAX_TEMP)
        self.max_temp_layout.addWidget(QLabel("Max Temp (C)"))
        self.max_temp_layout.addWidget(self.max_temp)
        self.sidebar.addLayout(self.max_temp_layout)

        self.min_temp_layout=QHBoxLayout()
        self.min_temp=QSpinBox()
        self.min_temp.valueChanged[int].connect(self.camera_worker.set_min_temp)
        self.min_temp.setValue(DEFAULT_MIN_TEMP)
        self.min_temp_layout.addWidget(QLabel("Min Temp (C)"))
        self.min_temp_layout.addWidget(self.min_temp)
        self.sidebar.addLayout(self.min_temp_layout)

        self.sidebar.addStretch(1)
        self.sidebar.addWidget(QLabel("Interpolation"))
        self.interpolation_method=QComboBox()
        self.interpolation_method.currentTextChanged.connect(self.camera_worker.set_interpolation_method)
        self.interpolation_method.addItem("Nearest")
        self.interpolation_method.addItem("Linear")
        self.interpolation_method.addItem("Cubic")
        self.sidebar.addWidget(self.interpolation_method)
        self.sidebar.addStretch(1)

        self.sidebar.addWidget(QLabel("Color Map"))
        self.colormap=QComboBox()
        self.colormap.currentTextChanged.connect(self.camera_worker.set_cmap)
        self.colormap.addItem("Seismic")
        self.colormap.addItem("Rainbow")
        self.colormap.addItem("CoolWarm")
        self.colormap.addItem("Plasma")
        self.colormap.addItem("Inferno")
        self.colormap.addItem("Jet")
        self.sidebar.addWidget(self.colormap)
        self.sidebar.addStretch(1)

        self.cursor_layout=QHBoxLayout()
        self.cursor=QCheckBox()
        self.cursor.setTristate(False)
        self.cursor.toggle()
        self.cursor.stateChanged.connect(self.camera_worker.set_draw_at_point)
        self.cursor_layout.addWidget(QLabel("Cursor"))
        self.cursor_layout.addWidget(self.cursor)
        self.sidebar.addLayout(self.cursor_layout)

        self.stats=QLabel("Max: --\nMean: --\nMin: --\nCursor: --")
        self.sidebar.addWidget(self.stats)
        
        grid=QGridLayout()
        up=QPushButton("^")
        up.clicked.connect(self.camera_worker.cursor_up)
        grid.addWidget(up,1,2)
        down=QPushButton("v")
        grid.addWidget(down,3,2)
        down.clicked.connect(self.camera_worker.cursor_down)
        left=QPushButton("<")
        left.clicked.connect(self.camera_worker.cursor_left)
        grid.addWidget(left,2,1)
        right=QPushButton(">")
        right.clicked.connect(self.camera_worker.cursor_right)
        grid.addWidget(right,2,3)

        self.sidebar.addLayout(grid)

        
        self.window.setLayout(self.main_layout)
        self.window.show()
        self.last_frame_time=time.time()
        self.accumulated_delta=1.0
        self.camera_worker.start()
    def stats_callback(self,stats):
        now=time.time()
        delta=now-self.last_frame_time
        self.last_frame_time=now
        self.accumulated_delta=0.5*(self.accumulated_delta+delta)
        stats['fr']=1.0/delta
        if self.cursor.checkState()>0:
           self.stats.setText(
            "Max: {max:.1f}\nMean: {mean:.1f}\nMin: {min:.1f}\nCursor: {at_point:.1f}\nFramerate: {fr:.1f}".format(**stats)
            )
        else:
           self.stats.setText(
            "Max: {max:.1f}\nMean: {mean:.1f}\nMin: {min:.1f}\nCursor: --\nFramerate: {fr:.1f}".format(**stats)
            )
    def run(self):
        self.app.exec_()
t=ThermalApp()
t.run()
