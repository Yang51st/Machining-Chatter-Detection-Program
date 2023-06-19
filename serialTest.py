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
import csv

timeI=[] #Stores the time at which sensor readings have been taken.
accelX=[] #Stores the raw voltage readings that will be calculated for acceleration readings.
accelY=[] #Stores the raw voltage readings that will be calculated for acceleration readings.

MAX_REQUESTS = 91  # The number of eStreamRead calls that will be performed. Time taken for this is usually half the value, in seconds.

# Open first found LabJack
handle = ljm.openS("ANY", "ANY", "ANY")  # Any device, Any connection, Any identifier
#handle = ljm.openS("T7", "ANY", "ANY")  # T7 device, Any connection, Any identifier
#handle = ljm.openS("T4", "ANY", "ANY")  # T4 device, Any connection, Any identifier
#handle = ljm.open(ljm.constants.dtANY, ljm.constants.ctANY, "ANY")  # Any device, Any connection, Any identifier

info = ljm.getHandleInfo(handle)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

deviceType = info[0]

# Stream Configuration
aScanListNames = ["AIN0","AIN3"]  # Scan list names to stream
numAddresses = len(aScanListNames)
aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
scanRate = 8000 #Ideally, the sampling frequency would be this value in Hz.
scansPerRead = int(scanRate / 2)

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
        ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)

        # Enabling internally-clocked stream.
        ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)

        # All negative channels are single-ended, AIN0 and AIN1 ranges are
        # +/-10 V, stream settling is 0 (default) and stream resolution index
        # is 0 (default).
        aNames = ["AIN_ALL_NEGATIVE_CH", "AIN0_RANGE", "AIN3_RANGE",
                  "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [ljm.constants.GND, 10.0, 10.0, 0, 0]
    # Write the analog inputs' negative channels (when applicable), ranges,
    # stream settling time and stream resolution configuration.
    numFrames = len(aNames)
    ljm.eWriteNames(handle, numFrames, aNames, aValues)

    # Configure and start stream
    scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)
    print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

    print("\nPerforming %i stream reads." % MAX_REQUESTS)
    start = datetime.now()
    totScans = 0
    totSkip = 0  # Total skipped samples

    i = 1

    while i <= MAX_REQUESTS:
        ret = ljm.eStreamRead(handle)

        aData = ret[0] #The variable aData will contain alternating readings from both channels since it scans in order.
        scans = len(aData) / numAddresses
        totScans += scans

        # Count the skipped samples which are indicated by -9999 values. Missed
        # samples occur after a device's stream buffer overflows and are
        # reported after auto-recover mode ends.
        curSkip = aData.count(-9999.0)
        totSkip += curSkip

        print("\neStreamRead %i" % i)
        ainStr = ""
        for j in range(0, numAddresses):
            ainStr += "%s = %0.5f, " % (aScanListNames[j], aData[j])
        print("  1st scan out of %i: %s" % (scans, ainStr))
        print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
              "%i" % (curSkip/numAddresses, ret[1], ret[2]))
        accelX+=aData[0::2] #Separating out the readings from AIN0, which will be along the X axis.
        accelY+=aData[1::2] #Separating out the readings from AIN3, which will be along the Y axis.
        i += 1

    end = datetime.now()

    print("\nTotal scans = %i" % (totScans))
    tt = (end - start).seconds + float((end - start).microseconds) / 1000000
    print("Time taken = %f seconds" % (tt))
    print("LJM Scan Rate = %f scans/second" % (scanRate))
    print("Timed Scan Rate = %f scans/second" % (totScans / tt)) #The actual sampling frequency.
    print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
    print("Skipped scans = %0.0f" % (totSkip / numAddresses))

    elapse=tt/len(accelY) #Calculating the average elapsed time for a reading to take place.
    for k in range(len(accelY)): #Adding in the calculated times for when each reading should have taken place.
        timeI.append(elapse*k)

except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

try:
    print("\nStop Stream")
    ljm.eStreamStop(handle)
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

# Close handle
ljm.close(handle)

filename="PCB_F18IN_T100_D0p125IN1.csv"
with open(filename, 'w',newline="") as csvfile:
    csvwriter = csv.writer(csvfile)
    for reading in range(int(scanRate),len(accelX)): #Skipping the first second of data, which contains skipped scans.
        csvwriter.writerow([timeI[reading]-timeI[scanRate],accelX[reading],accelY[reading]]) #Data made to still start at 0 seconds.

#Plotting the raw voltage readings that will end up being calculated for acceleration data.
plt.figure(1)
plt.plot(timeI[int(scanRate):],accelX[int(scanRate):])
plt.plot(timeI[int(scanRate):],accelY[int(scanRate):])
plt.show()