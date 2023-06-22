#AIN0 is X-axis, AIN3 is Y-axis.
#Black is X, Silver is Y.
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
from statistics import mean
import csv
import RestfulAPIBase as Base
from math import tan, pi

class ChatterDetector:
    def __init__(self):
        self.times=[] #Stores the time at which sensor readings have been taken.
        self.accelX=[] #Stores the acceleration readings on the X-axis.
        self.accelY=[] #Stores the acceleration readings on the Y-axis.
        self.X_AXIS_SENSITIVITY=0.001156 #Obtained from sensor callibration sheet.
        self.Y_AXIS_SENSITIVITY=0.001055 #Obtained from sensor callibration sheet.
        self.X_AXIS_OFFSET=-290.337933013119 #Calculated experimentally from X-axis readings.
        self.Y_AXIS_OFFSET=-366.66280307069917 #Calculated experimentally from Y-axis readings.
        self.start=-999 #Time at which a batch of readings begins.
        self.end=-999 #Time at which a batch of readings ends.
        self.handle=None
        self.aScanListNames=[]
        self.numAddresses=0
        self.scanRate=0
        self.totSkip=0
        self.totScans=0
        self.interface=Base.RestfulInterface()
        self.stockX=0
        self.stockY=0
        self.stockZ=0
        self.millFeed=0
        self.toolEngagement=0
        self.inclineAngle=0

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
        self.scanRate = 8000 #Ideally, the sampling frequency would be this value in Hz.
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

    def StartChatterMonitor(self):
        i = 1
        try:
            while i<91:
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
                self.accelX+=aData[0::2] #Separating out the readings from AIN0, which will be along the X axis.
                self.accelY+=aData[1::2] #Separating out the readings from AIN3, which will be along the Y axis.
                i += 1

            self.end = datetime.now()

            print("\nTotal scans = %i" % (self.totScans))
            tt = (self.end - self.start).seconds + float((self.end - self.start).microseconds) / 1000000
            print("Time taken = %f seconds" % (tt))
            print("LJM Scan Rate = %f scans/second" % (self.scanRate))
            print("Timed Scan Rate = %f scans/second" % (self.totScans / tt)) #The actual sampling frequency.
            print("Timed Sample Rate = %f samples/second" % (self.totScans * self.numAddresses / tt))
            print("Skipped scans = %0.0f" % (self.totSkip / self.numAddresses))

            elapse=tt/len(self.accelY) #Calculating the average elapsed time for a reading to take place.
            for k in range(len(self.accelY)): #Adding in the calculated times for when each reading should have taken place.
                self.times.append(elapse*k)

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

        # Close handle
        ljm.close(self.handle)
        timeOffsetAmount=self.times[int(self.scanRate)] #Amount to shift time readings by to get data starting at 0 seconds.
        for reading in range(int(self.scanRate),len(self.accelX)): #Skipping the first second of data, which contains skipped scans.
            self.times[reading]=self.times[reading]-timeOffsetAmount
            self.accelX[reading]=self.accelX[reading]/self.X_AXIS_SENSITIVITY #Scaling data from X-axis sensor to measure acceleration in meters per second squared.
            self.accelY[reading]=self.accelY[reading]/self.Y_AXIS_SENSITIVITY #Scaling data from Y-axis sensor to measure acceleration in meters per second squared.

        #Removing first second of bad data and aligning the acceleration readings to start and end at 0.
        self.times=self.times[int(self.scanRate):]
        self.accelX=self.accelX[int(self.scanRate):]
        self.accelY=self.accelY[int(self.scanRate):]
        self.accelX=signal.detrend(self.accelX,type="constant")
        self.accelY=signal.detrend(self.accelY,type="constant")

        filename="PCB_F18IN_T50_D0p25IN4.csv"
        with open(filename, 'w',newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            for reading in range(len(self.accelX)): #Skipping the first second of data, which contains skipped scans.
                csvwriter.writerow([self.times[reading],self.accelX[reading],self.accelY[reading]]) #Data made to still start at 0 seconds.

        #Plotting the raw voltage readings that will end up being calculated for acceleration data.
        plt.figure(1)
        plt.plot(self.times,self.accelX)
        plt.plot(self.times,self.accelY)
        plt.show()

    def PromptSpindleSpeedIncrease(self):
        print("Increase Spindle Speed by 5 percent.")

    def PromptSpindleSpeedDecrease(self):
        print("Decrease Spindle Speed by 5 percent.")

    def CalculateDepthOfCut(self):
        toolPositionX=self.interface.GetMachinePositionX()
        depthOfCut=tan(self.inclineAngle*pi/180.0)*toolPositionX
        
    def GetMachineSettings(self):
        self.millFeed=float(input("Enter Mill Feed in in/min."))
        self.toolEngagement=float(input("Enter Percent Tool Engagement."))
        self.inclineAngle=float(input("Enter angle of workpiece incline."))
        #Attempt to get workpiece dimensions from API.