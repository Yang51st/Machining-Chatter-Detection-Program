#AIN0 is X-axis, AIN3 is Y-axis.
#Black is X, Silver is Y.
#Always cut along X-axis.
"""
Demonstrates how to stream using the eStream functions.
Relevant Documentation:
LJM Library:
    LJM Library Installer:
        https://labjack.com/support/software/installers/ljm
    LJM Users Guide:
        https://labjack.com/support/software/api/ljm
    Opening and Closing:
        https://labjack.com/support/software/api/ljm/function-reference/opening-and-closing
    Constants:
        https://labjack.com/support/software/api/ljm/constants
    Stream Functions:
        https://labjack.com/support/software/api/ljm/function-reference/stream-functions
T-Series and I/O:
    Modbus Map:
        https://labjack.com/support/software/api/modbus/modbus-map
    Stream Mode:
        https://labjack.com/support/datasheets/t-series/communication/stream-mode
    Analog Inputs:
        https://labjack.com/support/datasheets/t-series/ain
Note:
    Our Python interfaces throw exceptions when there are any issues with
    device communications that need addressed. Many of our examples will
    terminate immediately when an exception is thrown. The onus is on the API
    user to address the cause of any exceptions thrown, and add exception
    handling when appropriate. We create our own exception classes that are
    derived from the built-in Python Exception class and can be caught as such.
    For more information, see the implementation in our source code and the
    Python standard documentation.
"""

from datetime import datetime
import sys
import numpy as np
from scipy.integrate import cumtrapz
from scipy import signal
import matplotlib.pyplot as plt
import time
from labjack import ljm
from scipy.signal import butter
from scipy.optimize import curve_fit
import csv
import RestfulAPIBase as Base
from math import tan, pi
import statistics

class ChatterDetector:
    def __init__(self):
        self.X_AXIS_SENSITIVITY=0.001156 #Obtained from sensor callibration sheet.
        self.X_AXIS_OFFSET=-290.337933013119 #Calculated experimentally from X-axis readings.
        self.Y_AXIS_SENSITIVITY=0.001055 #Obtained from sensor callibration sheet.
        self.Y_AXIS_OFFSET=-366.66280307069917 #Calculated experimentally from Y-axis readings.

        self.samplingFrequency=8000 #The frequency, in Hz, that sensor data is being read at.
        self.timeWindow=0.3 #Length of the period of time that will be analyzed for chatter.
        self.timeResolution=0.1 #The time between chatter indicator readings.
        self.start=-999 #Time at which a batch of readings begins.
        self.end=-999 #Time at which a batch of readings ends.
        self.recording=False #Variable that determines if vibration measurements will be taken.

        self.handle=None
        self.aScanListNames=[]
        self.numAddresses=0
        self.scanRate=0
        self.totSkip=0
        self.totScans=0

        self.interface=None
        self.MachineOffsetX=431.85 #Offset of the machine coordinate along X from the part zero. Unit is in millimetres.
        self.MachineOffsetZ=-492.277 #Offset of the machine coordinate along Z from the part zero. Unit is in millimetres.
        self.MaterialLengthX=4.12*25.4 #Length of the workpiece in millimetres.
        self.inclineAngle=7 #This measure is in degrees.

        self.lobeRPM=[]
        self.lobeDepth=[]

    def butter_highpass(self,N, Wn): #Helper function to apply Butterworth filter to data.
        return butter(N,Wn,'high',output="sos")

    def butter_highpass_filter(self,data, N,Wn): #Function to apply Butterworth filter to data.
        sos = self.butter_highpass(N,Wn)
        y = signal.sosfilt(sos, data)
        return y

    def ConnectMachine(self):
        self.interface=Base.RestfulInterface()

    def ConnectDAQ(self):
        # Open first found LabJack
        self.handle = ljm.openS("ANY", "ANY", "ANY")  # Any device, Any connection, Any identifier
        #handle = ljm.openS("T7", "ANY", "ANY")  # T7 device, Any connection, Any identifier
        #handle = ljm.openS("T4", "ANY", "ANY")  # T4 device, Any connection, Any identifier
        #handle = ljm.open(ljm.constants.dtANY, ljm.constants.ctANY, "ANY")  # Any device, Any connection, Any identifier

        info = ljm.getHandleInfo(self.handle)
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
            "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
            (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

        deviceType = info[0]

        # Stream Configuration
        self.aScanListNames = ["AIN0","AIN3"]  # Scan list names to stream
        self.numAddresses = len(self.aScanListNames)
        aScanList = ljm.namesToAddresses(self.numAddresses, self.aScanListNames)[0]
        self.scanRate = self.samplingFrequency #Ideally, the sampling frequency would be this value in Hz.
        scansPerRead = int(self.scanRate / 2)

        try:
            # When streaming, negative channels and ranges can be configured for
            # individual analog inputs, but the stream has only one settling time and
            # resolution.

            if deviceType == ljm.constants.dtT4:
                # LabJack T4 configuration

                # AIN0 and AIN1 ranges are +/-10 V, stream settling is 0 (default) and
                # stream resolution index is 0 (default).
                aNames = ["AIN0_RANGE", "AIN1_RANGE", "STREAM_SETTLING_US",
                        "STREAM_RESOLUTION_INDEX"]
                aValues = [10.0, 10.0, 0, 0]
            else:
                # LabJack T7 and other devices configuration

                # Ensure triggered stream is disabled.
                ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

                # Enabling internally-clocked stream.
                ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

                # All negative channels are single-ended, AIN0 and AIN1 ranges are
                # +/-10 V, stream settling is 0 (default) and stream resolution index
                # is 0 (default).
                aNames = ["AIN_ALL_NEGATIVE_CH", "AIN0_RANGE", "AIN3_RANGE",
                        "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
                aValues = [ljm.constants.GND, 10.0, 10.0, 0, 0]
            # Write the analog inputs' negative channels (when applicable), ranges,
            # stream settling time and stream resolution configuration.
            numFrames = len(aNames)
            ljm.eWriteNames(self.handle, numFrames, aNames, aValues)

            # Configure and start stream
            self.scanRate = ljm.eStreamStart(self.handle, scansPerRead, self.numAddresses, aScanList, self.scanRate)
            print("\nStream started with a scan rate of %0.0f Hz." % self.scanRate)

            print("\nPerforming stream reads.")
            self.start = datetime.now()

        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)

    def RecordCut(self):
        while True:
            if self.Ready():
                break
        while True:
            if self.interface.GetRapidPercentage()>0:
                break
        self.ConnectDAQ()
        times=[] #Stores the time at which sensor readings have been taken.
        accelX=[] #Stores the acceleration readings on the X-axis.
        accelY=[] #Stores the acceleration readings on the Y-axis.
        loadT=[] #Stores the time at which load percentages are recorded.
        loadS=[] #Stores the percent load on the given axis.
        loadX=[] #Stores the percent load on the given axis.
        loadY=[] #Stores the percent load on the given axis.
        loadZ=[] #Stores the percent load on the given axis.
        tChatter=[] #Stores the time at which chatter indicators were calculated.
        yChatter=[] #Stores the chatter indicator values calculated.
        startWindow=0 #Beginning index of the 0.3 second period that will be analyzed for chatter.
        endWindow=0 #Ending index of the 0.3 second window that will be analyzed for chatter.
        addCI=True #Variable that determines if a calculated chatter indicator will be used for stability lobe creation.
        timeIndex=5 #Index at which chatter detection program will begin, so as to avoid skipped scans in data.

        N,Wn=signal.buttord(0.05,0.0375,3,40) #Calculating the parameters for a Butterworth filter for processing the sensor data.

        spindleSpeed=self.interface.GetSpindleSpeed()
        revolutionTime=60/spindleSpeed #Calculates how long, in seconds, a revolution of the spindle takes.

        i = 1
        try:
            while self.recording:
                self.CheckForStop()
                ret = ljm.eStreamRead(self.handle)

                aData = ret[0] #The variable aData will contain alternating readings from both channels since it scans in order.
                scans = len(aData) / self.numAddresses
                self.totScans += scans

                # Count the skipped samples which are indicated by -9999 values. Missed
                # samples occur after a device's stream buffer overflows and are
                # reported after auto-recover mode ends.
                curSkip = aData.count(-9999.0)
                self.totSkip += curSkip

                print("\neStreamRead %i" % i)
                ainStr = ""
                for j in range(0, self.numAddresses):
                    ainStr += "%s = %0.5f, " % (self.aScanListNames[j], aData[j])
                print("  1st scan out of %i: %s" % (scans, ainStr))
                print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                    "%i" % (curSkip/self.numAddresses, ret[1], ret[2]))
                xBuf=aData[0::2] #Separating out the readings from AIN0, which will be along the X axis.
                yBuf=aData[1::2] #Separating out the readings from AIN3, which will be along the Y axis.
                tBuf=[]
                intervalTime=0.5/len(xBuf)
                for j in range(len(xBuf)):
                    tBuf.append(intervalTime*j+0.5*(i-1))
                    xBuf[j]=xBuf[j]/self.X_AXIS_SENSITIVITY-self.X_AXIS_OFFSET
                    yBuf[j]=yBuf[j]/self.Y_AXIS_SENSITIVITY-self.Y_AXIS_OFFSET
                accelX+=xBuf
                accelY+=yBuf
                times+=tBuf
                loadT.append(tBuf[-1])
                loadS.append(self.interface.GetSpindleLoad())
                loadX.append(self.interface.GetAxisXLoad())
                loadY.append(self.interface.GetAxisYLoad())
                loadZ.append(self.interface.GetAxisZLoad())
                i += 1

                while True:
                    startWindow=timeIndex*self.samplingFrequency*self.timeResolution
                    endWindow=startWindow+self.timeWindow*self.samplingFrequency
                    if endWindow>=len(times):
                        break
                    startWindow=int(startWindow)
                    endWindow=int(endWindow)
                    filtTime=times[startWindow:endWindow]

                    filtaccelX=accelX[startWindow:endWindow]
                    filtaccelX=signal.detrend(filtaccelX,type="linear")
                    filtaccelX=self.butter_highpass_filter(filtaccelX,N,Wn)
                    veloX=cumtrapz(filtaccelX,filtTime,initial=0.0)
                    veloX=signal.detrend(veloX, type="linear")
                    dispX=cumtrapz(veloX,filtTime,initial=0.0)

                    filtaccelY=accelY[startWindow:endWindow]
                    filtaccelY=signal.detrend(filtaccelY,type="linear")
                    filtaccelY=self.butter_highpass_filter(filtaccelY,N,Wn)
                    veloY=cumtrapz(filtaccelY,filtTime,initial=0.0)
                    veloY=signal.detrend(veloY, type="linear")
                    dispY=cumtrapz(veloY,filtTime,initial=0.0)

                    prevTim=filtTime[0]
                    bisX=[] #Stores X-value of bisection points.
                    bisY=[] #Stores Y-value of bisection points.
                    for tindex in range(len(filtTime)):
                        if filtTime[tindex]>=(prevTim+revolutionTime): #Checks to see if enough time has passed for a full rotation,
                            bisX.append(dispX[tindex])                 #meaning that the bisection point would ideally be in the same position again.
                            bisY.append(dispY[tindex])
                            prevTim=filtTime[tindex]

                    #Taking the standard deviation of the bisection points and of the overall trajectory, then calculating the chatter indicator from them.
                    sX=statistics.stdev(bisX)
                    sY=statistics.stdev(bisY)
                    tX=statistics.stdev(dispX)
                    tY=statistics.stdev(dispY)
                    chatterIndicator=sX*sY/(tX*tY)
                    tChatter.append(timeIndex*self.timeResolution+self.timeWindow)
                    yChatter.append(chatterIndicator)
                    if chatterIndicator>0.9 and self.InBounds():
                        print("Hit Stop Cycle")
                        if addCI and self.InBounds():
                            self.lobeRPM.append(self.interface.GetSpindleSpeed())
                            self.lobeDepth.append(self.GetDepthOfCut(type="incline"))
                            addCI=False
                    timeIndex+=1

            self.end = datetime.now()

            print("\nTotal scans = %i" % (self.totScans))
            tt = (self.end - self.start).seconds + float((self.end - self.start).microseconds) / 1000000
            print("Time taken = %f seconds" % (tt))
            print("LJM Scan Rate = %f scans/second" % (self.scanRate))
            print("Timed Scan Rate = %f scans/second" % (self.totScans / tt)) #The actual sampling frequency.
            print("Timed Sample Rate = %f samples/second" % (self.totScans * self.numAddresses / tt))
            print("Skipped scans = %0.0f" % (self.totSkip / self.numAddresses))

        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)

        try:
            print("\nStop Stream")
            ljm.eStreamStop(self.handle)
        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)

        ljm.close(self.handle)

        #Removing first second of bad data and aligning the acceleration readings to start and end at 0.
        times=times[int(self.scanRate):]
        accelX=accelX[int(self.scanRate):]
        accelY=accelY[int(self.scanRate):]
        accelX=signal.detrend(accelX,type="linear")
        accelY=signal.detrend(accelY,type="linear")
        timestamp=datetime.now()
        filename="PCB_"+str(timestamp.month)+"_"+str(timestamp.day)+"_"+str(timestamp.hour)+"_"+str(timestamp.minute)+"_"+str(int(spindleSpeed))+".csv"
        loader=0
        with open(filename, 'w',newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            for reading in range(len(accelX)):
                if reading==0:
                    csvwriter.writerow(["Time (s)","Accel X (m/s^2)","Accel Y (m/s^2)","Load S (%)","Load X (%)","Load Y (%)","Load Z (%)"])
                if times[reading]>loadT[loader] and loader<len(loadT):
                    loader+=1
                csvwriter.writerow([times[reading],accelX[reading],accelY[reading],loadS[loader],loadX[loader],loadY[loader],loadZ[loader]])

        #Plotting the raw voltage readings that will end up being calculated for acceleration data.
        plt.figure(1)
        plt.plot(tChatter,yChatter)
        plt.plot(tChatter,yChatter,"ro")
        plt.show()

    def PromptSpindleSpeedIncrease(self):
        print("Increase Spindle Speed by 5 percent.")

    def PromptSpindleSpeedDecrease(self):
        print("Decrease Spindle Speed by 5 percent.")

    def GetDepthOfCut(self,type="flat"):
        if type=="incline":
            toolPositionX=self.interface.GetMachinePositionX()
            depthOfCut=tan(self.inclineAngle*pi/180.0)*(toolPositionX-self.MachineOffsetX)
            return (depthOfCut/25.4) #Result will be in inches.
        else:
            toolPositionZ=self.interface.GetMachinePositionZ()
            depthOfCut=toolPositionZ-self.MachineOffsetZ
            return (depthOfCut/25.4) #Result will be in inches.

    def long_function(self,n,x1,x2,x3,x4,c2,c3,c4):
        return 1/(2*x1*abs(np.minimum(np.real(-(x2+c2*1j)/(n**2*1j/(x3+c3*1j)+(x4+c4*1j)*1j*n/(x3+c3*1j)+1)),np.array([0 for kk in range(len(n))]))))
        #Above is the equation from the 2021 Brecher paper. Note how some of the constants are actually complex, so extra unknowns are added.

    def CreateStabilityLobe(self):
        timestamp=datetime.now()
        filename="Stability_Lobe_Points_For_"+str(timestamp.month)+"_"+str(timestamp.day)+"_"+str(timestamp.hour)+"_"+str(timestamp.minute)+".csv"
        with open(filename, 'w',newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            for reading in range(len(self.lobeRPM)):
                csvwriter.writerow([self.lobeRPM[reading],self.lobeDepth[reading]])

        popt,pcov=curve_fit(self.long_function,np.array(self.lobeRPM),np.array(self.lobeDepth),maxfev=900000) #Fitting a curve, with a high maxfev value to give enough time for calculation.
        yFit=self.long_function(np.array([k for k in range(1000,15000)]),*popt) #Getting the Y values of points on the fitted curve.
        plt.plot(np.array([k for k in range(1000,15000)]),yFit) #Plotting the curve fitted to the data.
        plt.plot(self.lobeRPM,self.lobeDepth,"k.")
        plt.show()

        timestamp=datetime.now()
        filename="Stability_Lobe_Constants_For_"+str(timestamp.month)+"_"+str(timestamp.day)+"_"+str(timestamp.hour)+"_"+str(timestamp.minute)+".csv"
        with open(filename, 'w',newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(list(popt))
    
    def Ready(self):
        if self.interface.GetRapidPercentage()==0 and self.recording==False:
            self.recording=True
            return True
        else:
            return False
        
    def CheckForStop(self):
        if self.interface.IsStopped():
            self.recording=False

    def InBounds(self):
        toolPositionX=self.interface.GetMachinePositionX()
        if (self.MachineOffsetX+10)<=toolPositionX<=(self.MachineOffsetX+self.MaterialLengthX-10):
            return True
        else:
            return False

    def MachineShutdown(self):
        # Close connection with machine.
        self.interface.Shutdown()