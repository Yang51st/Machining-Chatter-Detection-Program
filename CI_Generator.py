import os
import csv
from scipy.integrate import cumtrapz
from scipy import signal
import matplotlib.pyplot as plt
from scipy.signal import butter
import statistics

directory = "VibrationData/HurcoVMX42Di/Aluminum/End Mill/0p5IN/12000RPM"

for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    # checking if it is a file
    if os.path.isfile(f):

        accelX=[]
        timeXF=[] #Stores the time at which sensor readings have been taken.
        accelY=[]
        timeYF=[] #Stores the time at which sensor readings have been taken.

        filename=f
        with open(filename,mode="r") as file:
            csvFile = csv.reader(file)
            for lines in csvFile:
                try: #Skip the lines of data at the beginning that do not contain sensor readings.
                    timeXF.append(float(lines[0]))
                    accelX.append(float(lines[1]))
                except:
                    pass
        with open(filename,mode="r") as file:
            csvFile = csv.reader(file)
            for lines in csvFile:
                try: #Skip the lines of data at the beginning that do not contain sensor readings.
                    timeYF.append(float(lines[0]))
                    accelY.append(float(lines[2]))
                except:
                    pass

        accelX=signal.detrend(accelX,type="constant")
        accelY=signal.detrend(accelY,type="constant")

        PCB_RATE=8000 #Sampling frequency of PCB wired sensor.
        EBI_RATE=1600 #Sampling frequency of EBI bluetooth sensor.

        f_sample=8000
        SPINDLE_RPM=12000

        """settings=filename.split("_")
        for item in settings:
            if item.find("PCB")!=-1 or item.find("PFC")!=-1:
                f_sample=PCB_RATE
            if item.find("EBI")!=-1:
                f_sample=EBI_RATE
            if item.find("RPM")!=-1:
                SPINDLE_RPM=int(item[:item.find("RPM")])
                break
        else:
            SPINDLE_RPM=input("Please enter spindle RPM for",filename)"""

        f_pass=200 #Pass frequency in Hz.
        f_stop=150 #Stop frequency in Hz.
        wp=f_pass/(f_sample/2) #Calculated omega pass frequency for analog filtering.
        ws=f_stop/(f_sample/2) #Calculated omega stop frequency for analog filtering.
        g_pass=3 #Pass loss in dB.
        g_stop=40 #Stop attenuation in dB.
        N,Wn=signal.buttord(wp,ws,g_pass,g_stop)

        def butter_highpass(N, Wn): #Helper function to apply Butterworth filter to data.
            return butter(N,Wn,'high',output="sos")

        def butter_highpass_filter(data, N,Wn): #Function to apply Butterworth filter to data.
            sos = butter_highpass(N,Wn)
            y = signal.sosfilt(sos, data)
            return y

        windowTime=0.3 #A range of 0.3 seconds of data will be analyzed at a time.
        revolutionTime=60/SPINDLE_RPM #Time it takes for the spindle to rotate a full term. Used to approximate bisection point timings.
        poincare=6.9 #The specific time of the poincare section that will be graphed so bisection point and trajectory plotting can be verified.
        packageResolution=0.1 #Every 0.1 seconds, a new window of data will be analyzed.
        lens=int(len(timeXF)/timeXF[-1]*packageResolution) #Calculates how many readings will be analyzed at a time.

        windex=0 #The index of the window of data currently being analyzed.
        chatsT=[] #Stores the time at which chatter indicators are calculated.
        chatsI=[] #Stores the value of calculated chatter indicators.

        while True:
            startW=int(windex*lens) #Calculates the starting index for the analysis window.
            endW=int(lens*windowTime/packageResolution+startW) #Calculates the ending index for the analysis window.
            
            if endW>=len(timeXF): #In case the ending index goes out of bounds of the data taken.
                break

            timeX=timeXF[startW:endW] #Creating a new array that will temporarily store the times for the readings in the analysis window.
            timeY=timeYF[startW:endW] #Creating a new array that will temporarily store the times for the readings in the analysis window.

            filtaccelX=accelX[startW:endW]
            filtaccelX=signal.detrend(filtaccelX, type="linear")
            filtaccelX=butter_highpass_filter(filtaccelX,N,Wn)

            filtaccelY=accelY[startW:endW]
            filtaccelY=signal.detrend(filtaccelY, type="linear")
            filtaccelY=butter_highpass_filter(filtaccelY,N,Wn)

            veloX=cumtrapz(filtaccelX,timeX,initial=0.0)
            veloY=cumtrapz(filtaccelY,timeY,initial=0.0)
            veloX=signal.detrend(veloX, type="linear")
            veloY=signal.detrend(veloY, type="linear")
            dispX=cumtrapz(veloX,timeX,initial=0.0)
            dispY=cumtrapz(veloY,timeY,initial=0.0)

            prevTim=timeX[0]
            bisX=[] #Stores X-value of bisection points.
            bisY=[] #Stores Y-value of bisection points.
            for tindex in range(len(timeX)):
                if timeX[tindex]>=(prevTim+revolutionTime): #Checks to see if enough time has passed for a full rotation,
                    bisX.append(dispX[tindex])              #meaning that the bisection point would ideally be in the same position again.
                    bisY.append(dispY[tindex])
                    prevTim=timeX[tindex]
            if windex==(poincare*10-windowTime/packageResolution):
                """
                plt.figure(1)
                plt.clf()
                plt.plot(timeX,filtaccelX,label="accelerationX")
                plt.plot(timeY,filtaccelY,label="accelerationY")
                plt.legend(facecolor = 'gray', title = 'Legend',loc = 'upper left')
                plt.figure(2)
                plt.clf()
                plt.plot(timeX,veloX,label="velocityX")
                plt.plot(timeY,veloY,label="velocityY")
                plt.legend(facecolor = 'gray', title = 'Legend',loc = 'upper left')
                plt.figure(3)
                plt.clf()
                plt.plot(timeX,dispX,label="displacementX")
                plt.plot(timeY,dispY,label="displacementY")
                plt.legend(facecolor = 'gray', title = 'Legend',loc = 'upper left')
                """

            #Taking the standard deviation of the bisection points and of the overall trajectory, then calculating the chatter indicator from them.
            sX=statistics.stdev(bisX)
            sY=statistics.stdev(bisY)
            tX=statistics.stdev(dispX)
            tY=statistics.stdev(dispY)
            chatterIndicator=sX*sY/(tX*tY)
            chatsT.append(windex*packageResolution+windowTime+2*timeXF[0]-timeXF[1])
            chatsI.append(chatterIndicator)

            windex+=1 #Moving on to calculate the next window of data.

        holder=[]
        with open(filename,mode="r") as file:
            csvFile = csv.reader(file)
            for lines in csvFile:
                holder.append(lines)
        with open(f,'w',newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            try:
                float(holder[0][0])
            except:
                csvwriter.writerow(holder[0]+["CI Value"])
                holder=holder[1:]
            CIindex=0
            for row in holder:
                if chatsT[CIindex]<=float(row[0]) and CIindex<len(chatsT)-1:
                    CIindex+=1
                csvwriter.writerow(row+[str(chatsI[CIindex])])