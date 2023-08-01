import csv
from scipy.integrate import cumtrapz
from scipy import signal
import matplotlib.pyplot as plt
from scipy.signal import butter
import statistics

DETECTION_RESOLUTION=0.1 #The region of time that will be monitored for changes in magnitude.
CHANGE_SENSITIVITY=2.5 #The relative change required to be considered a change in magnitude.

f_sample=8000 #Sampling frequency of PCB sensor in Hz.
f_pass=11000 #Pass frequency in Hz.
f_stop=10000 #Stop frequency in Hz.
wp=f_pass/(f_sample/2) #Calculated omega pass frequency for analog filtering.
ws=f_stop/(f_sample/2) #Calculated omega stop frequency for analog filtering.
g_pass=3 #Pass loss in dB.
g_stop=40 #Stop attenuation in dB.

def butter_highpass(N, Wn): #Helper function to apply Butterworth filter to data.
    return butter(N,Wn,'high',output="sos")

def butter_highpass_filter(data, N,Wn): #Function to apply Butterworth filter to data.
    sos = butter_highpass(N,Wn)
    y = signal.sosfilt(sos, data)
    return y

def openData(filename):
    timesT=[]
    accelX=[]
    accelY=[]
    with open(filename,mode="r") as file:
        csvFile = csv.reader(file)
        for lines in csvFile:
            try: #Skip the lines of data at the beginning that do not contain sensor readings.
                timesT.append(float(lines[0]))
                accelX.append(float(lines[1]))
                accelY.append(float(lines[2]))
            except:
                pass
    return timesT,accelX,accelY

def findJumps(timeT,values):
    breakpoints=[]
    prevT=timeT[0]
    runningAvg=[]
    prevA=0
    prevC=0
    for ind in range(len(timeT)):
        if timeT[ind]>=prevT+DETECTION_RESOLUTION:
            ampl=max(runningAvg)-min(runningAvg)
            cent=statistics.mean(runningAvg)
            runningAvg=[]
            prevT=timeT[ind]
            if abs(ampl-prevA)/max(abs(prevA),0.001)>CHANGE_SENSITIVITY or abs(cent-prevC)/max(abs(prevC),0.001)>CHANGE_SENSITIVITY:
                breakpoints.append(timeT[ind])
                prevA=ampl
                prevC=cent
        runningAvg.append(values[ind])
    return breakpoints

N,Wn=signal.buttord(wp,ws,g_pass,g_stop)

filename1="VibrationData/HurcoVMX42SRTi/CutsAlongX/UnalignedData/EBI_F18IN_T25_D0p125IN_3000RPM_5A_ON_TABLE.csv"
timesT1,accelX1,accelY1=openData(filename1)

filename2="VibrationData/HurcoVMX42SRTi/CutsAlongX/UnalignedData/EBI_F18IN_T25_D0p125IN_3000RPM_5A_ON_TABLE.csv"
timesT2,accelX2,accelY2=openData(filename2)

accelX1=signal.detrend(accelX1,type="constant")
accelY1=signal.detrend(accelY1,type="constant")
accelX1=butter_highpass_filter(accelX1,N,Wn)
accelY1=butter_highpass_filter(accelY1,N,Wn)
breakpoints1=findJumps(timesT1,accelY1)

plt.figure(1)
plt.clf()
plt.plot(timesT1,accelX1)
plt.plot(timesT1,accelY1)
plt.plot(breakpoints1,[0 for i in breakpoints1],"ro")
plt.show()