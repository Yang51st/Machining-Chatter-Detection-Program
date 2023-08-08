import csv
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
import wx
from scipy.integrate import cumtrapz
from scipy import signal
from scipy.signal import butter
import statistics

offset=0

filenamePCB="VibrationData/HurcoVMX42SRTi/CutsAlongZ/PCB_F18IN_T50_D0p125_3000RPM_5AVZ.csv"
timesPCB=[]
col1PCB=[]
col2PCB=[]

filenameEBI="VibrationData/HurcoVMX42SRTi/CutsAlongZ/UnalignedData/EBI_F18IN_T50_D0p125_3000RPM_5AVZ.csv"
timesEBI=[]
col1EBI=[]
col2EBI=[]
col3EBI=[]

def butter_highpass(N, Wn): #Helper function to apply Butterworth filter to data.
    return butter(N,Wn,'high',output="sos")

def butter_highpass_filter(data, N,Wn): #Function to apply Butterworth filter to data.
    sos = butter_highpass(N,Wn)
    y = signal.sosfilt(sos, data)
    return y

f_sample=8000 #Sampling frequency of PCB sensor in Hz.
f_pass=12000 #Pass frequency in Hz.
f_stop=10000 #Stop frequency in Hz.
wp=f_pass/(f_sample/2) #Calculated omega pass frequency for analog filtering.
ws=f_stop/(f_sample/2) #Calculated omega stop frequency for analog filtering.
g_pass=3 #Pass loss in dB.
g_stop=40 #Stop attenuation in dB.

NPCB,WnPCB=signal.buttord(wp,ws,g_pass,g_stop)
NEBI,WnEBI=signal.buttord(2*500/1600,2*400/1600,3,40)

class MyFrame(wx.Frame):
    def __init__(self, parent, id):
        wx.Frame.__init__(self,parent, id, 'Data Aligner',
                style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER,
                size=(800, 800))
        self.panel = wx.Panel(self, -1)
        self.fig = Figure((5, 4), 75)
        self.canvas = FigureCanvasWxAgg(self.panel, -1, self.fig)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, -1, wx.EXPAND)
        self.panel.SetSizer(sizer)
        self.panel.Fit()
        self.init_data()
        self.init_plot()
        self.scroll_range = len(self.tPCB)//2
        self.canvas.SetScrollbar(wx.HORIZONTAL, 0, 5,
                                 self.scroll_range)
        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
        self.canvas.Bind(wx.EVT_SCROLLWIN, self.OnScrollEvt)

    def init_data(self):

        # Get some data to plot:
        with open(filenamePCB,mode="r") as file:
            csvFile = csv.reader(file)
            global col1PCB
            global col2PCB
            for lines in csvFile:
                try:
                    timesPCB.append(float(lines[0]))
                    col1PCB.append(float(lines[1]))
                    col2PCB.append(float(lines[4]))
                except:
                    pass
            col1PCB=signal.detrend(col1PCB,type="constant")
            col2PCB=signal.detrend(col2PCB,type="constant")
            #col1PCB=butter_highpass_filter(col1PCB,NPCB,WnPCB)
            #col2PCB=butter_highpass_filter(col2PCB,NPCB,WnPCB)
            self.tPCB = timesPCB
            self.PCB = col2PCB

        with open(filenameEBI,mode="r") as file:
            csvFile = csv.reader(file)
            global col1EBI
            global col2EBI
            global col3EBI
            for lines in csvFile:
                try:
                    timesEBI.append(float(lines[0]))
                    col1EBI.append(float(lines[1]))
                    col2EBI.append(float(lines[2]))
                    col3EBI.append(float(lines[3]))
                except:
                    pass
            col1EBI=signal.detrend(col1EBI,type="constant")
            col2EBI=signal.detrend(col2EBI,type="constant")
            col3EBI=signal.detrend(col3EBI,type="constant")
            #col1EBI=butter_highpass_filter(col1EBI,NEBI,WnEBI)
            #col2EBI=butter_highpass_filter(col2EBI,NEBI,WnEBI)
            #col3EBI=butter_highpass_filter(col3EBI,NEBI,WnEBI)
            self.tEBI = timesEBI
            self.EBI = col2EBI

        # Extents of data sequence:
        self.i_min = 0
        self.i_max = len(self.tPCB)

        # Size of plot window:
        self.i_window = 8000*16

        # Indices of data interval to be plotted:
        self.i_start = 0
        self.i_end = self.i_start + self.i_window

    def init_plot(self):
        self.axesPCB = self.fig.add_subplot(211)
        self.plot_dataPCB =self.axesPCB.plot(self.tPCB[self.i_start:self.i_end],self.PCB[self.i_start:self.i_end])[0]
        self.axesEBI = self.fig.add_subplot(212)
        self.plot_dataEBI =self.axesEBI.plot(self.tEBI,self.EBI)[0]

    def draw_plot(self):
        self.plot_dataPCB.set_xdata(self.tPCB[self.i_start:self.i_end])
        self.plot_dataPCB.set_ydata(self.PCB[self.i_start:self.i_end])
        self.axesPCB.set_xlim((min(self.tPCB[self.i_start:self.i_end]),
                           max(self.tPCB[self.i_start:self.i_end])))
        self.axesPCB.set_ylim((min(self.PCB[self.i_start:self.i_end]),
                           max(self.PCB[self.i_start:self.i_end])))

        self.plot_dataEBI.set_xdata(self.tEBI[0:1600*16])
        self.plot_dataEBI.set_ydata(self.EBI[0:1600*16])
        self.axesEBI.set_xlim((min(self.tEBI[0:1600*16]),
                           max(self.tEBI[0:1600*16])))
        self.axesEBI.set_ylim((min(self.EBI[0:1600*16]),
                           max(self.EBI[0:1600*16])))

        # Redraw:
        self.canvas.draw()

    def OnClick(self, event):
        x, y = event.GetPosition()
        self.i_start+=int((x-400)/620*100)*500
        self.i_start=min([self.i_start,len(self.tPCB)-self.i_window])
        self.i_start=max([0,self.i_start])
        self.i_end+=int((x-400)/620*100)*500
        self.i_end=min([self.i_end,len(self.tPCB)])
        self.i_end=max([self.i_window,self.i_end])
        global offset
        offset=timesPCB[self.i_start]
        self.draw_plot()

    def update_scrollpos(self, new_pos):
        self.i_start = self.i_min + new_pos
        self.i_end = self.i_min + self.i_window + new_pos
        self.i_start=min([self.i_start,len(self.tPCB)-self.i_window])
        self.i_start=max([0,self.i_start])
        self.i_end=min([self.i_end,len(self.tPCB)])
        self.i_end=max([self.i_window,self.i_end])
        self.canvas.SetScrollPos(wx.HORIZONTAL, new_pos)
        global offset
        offset=timesPCB[self.i_start]
        self.draw_plot()

    def OnScrollEvt(self, event):
        evtype = event.GetEventType()

        if evtype == wx.EVT_SCROLLWIN_THUMBTRACK.typeId:
            pos = event.GetPosition()
            self.update_scrollpos(pos)
        elif evtype == wx.EVT_SCROLLWIN_LINEDOWN.typeId:
            pos = self.canvas.GetScrollPos(wx.HORIZONTAL)
            self.update_scrollpos(pos + 1)
        elif evtype == wx.EVT_SCROLLWIN_LINEUP.typeId:
            pos = self.canvas.GetScrollPos(wx.HORIZONTAL)
            self.update_scrollpos(pos - 1)
        elif evtype == wx.EVT_SCROLLWIN_PAGEUP.typeId:
            pos = self.canvas.GetScrollPos(wx.HORIZONTAL)
            self.update_scrollpos(pos - 10)
        elif evtype == wx.EVT_SCROLLWIN_PAGEDOWN.typeId:
            pos = self.canvas.GetScrollPos(wx.HORIZONTAL)
            self.update_scrollpos(pos + 10)

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame(parent=None,id=-1)
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()
    print("Done!")
    timesEBI=[]
    col1EBI=[]
    col2EBI=[]
    col3EBI=[]
    with open(filenameEBI,mode="r") as file:
        csvFile = csv.reader(file)
        for lines in csvFile:
            try:
                timesEBI.append(float(lines[0]))
                col1EBI.append(float(lines[1]))
                col2EBI.append(float(lines[2]))
                col3EBI.append(float(lines[3]))
            except:
                pass
    with open(filenameEBI,'w',newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        for reading in range(len(timesEBI)):
            if reading==0:
                csvwriter.writerow(["Time (s)","Accel X (m/s^2)","Accel Y (m/s^2)","Accel Z (m/s^2)"])
            csvwriter.writerow([timesEBI[reading]+offset,col1EBI[reading],col2EBI[reading],col3EBI[reading]])