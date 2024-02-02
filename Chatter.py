import csv
from scipy.integrate import cumtrapz
from scipy import signal
import matplotlib.pyplot as plt
from scipy.signal import butter
import statistics
import pandas as pd
import os
import imageio


class ChatterDetectionUtils:


    timeF=[] #Stores the time at which sensor readings have been taken.
    accelX=[]
    accelY=[]
    veloX=[]
    veloY=[]
    dispX=[]
    dispY=[]
    bisectionTimes=[]
    chatsT=[] #Stores the time at which chatter indicators are calculated.
    chatsI=[] #Stores the value of calculated chatter indicators.
    threshold=[]


    def __init__(self,filepath, spindle_speed, column_order="TXYZ", f_pass=50, f_stop=49):
        self.filename=filepath
        data_accel = pd.read_csv(filepath)
        col_list=list(data_accel)
        col_list[0], col_list[1], col_list[2] =[col_list[column_order.find("T")],
                                               col_list[column_order.find("X")],
                                               col_list[column_order.find("Y")]]
        data_accel=data_accel[col_list[:3]]
        self.timeF=list(data_accel.iloc[1:,0])
        self.accelX=list(data_accel.iloc[1:,1])
        self.accelY=list(data_accel.iloc[1:,2])
        timeOffset=self.timeF[0]
        for i in range(len(self.timeF)):
            self.timeF[i]-=timeOffset
        self.f_sample=int(len(self.timeF)/(self.timeF[-1]-self.timeF[0]))
        wp=f_pass/(self.f_sample/2) #Calculated omega pass frequency for analog filtering.
        ws=f_stop/(self.f_sample/2) #Calculated omega stop frequency for analog filtering.
        g_pass=3 #Pass loss in dB.
        g_stop=40 #Stop attenuation in dB.
        N,Wn=signal.buttord(wp,ws,g_pass,g_stop)
        filtaccelX=self.accelX
        filtaccelX=signal.detrend(filtaccelX, type="linear")
        filtaccelX=self.butter_highpass_filter(filtaccelX,N,Wn)
        filtaccelY=self.accelY
        filtaccelY=signal.detrend(filtaccelY, type="linear")
        filtaccelY=self.butter_highpass_filter(filtaccelY,N,Wn)
        self.veloX=cumtrapz(filtaccelX,self.timeF,initial=0.0)
        self.veloY=cumtrapz(filtaccelY,self.timeF,initial=0.0)
        self.veloX=signal.detrend(self.veloX, type="linear")
        self.veloY=signal.detrend(self.veloY, type="linear")
        self.dispX=cumtrapz(self.veloX,self.timeF,initial=0.0)
        self.dispY=cumtrapz(self.veloY,self.timeF,initial=0.0)
        self.dispX=signal.detrend(self.dispX, type="linear")
        self.dispY=signal.detrend(self.dispY, type="linear")
        bprev=self.timeF[0]
        self.revolution_time=60/spindle_speed
        for ts in range(len(self.timeF)):
            if self.timeF[ts]>=bprev+self.revolution_time:
                self.bisectionTimes.append(1)
                bprev=self.timeF[ts]
            else:
                self.bisectionTimes.append(0)


    def calculate_chatter_indicator(self, time_window, step_size,):
        w_length=int(self.f_sample*time_window) #Calculates how many readings will be analyzed at a time.
        s_length=int(self.f_sample*step_size)
        distsTrav=[]
        for w_index in range(0,len(self.timeF)-w_length,s_length):
            w_start=w_index
            w_end=w_start+w_length
            bisX=[] #Stores X-value of bisection points.
            bisY=[] #Stores Y-value of bisection points.
            metric=[]
            bisDist=0
            bds=[]
            for ts in range(w_start,w_end):
                if self.bisectionTimes[ts]:
                    bisX.append(self.dispX[ts])
                    bisY.append(self.dispY[ts])
                    metric.append(bisDist)
                    distsTrav.append(bisDist)
                    bisDist=0
                if ts+1<w_end:
                    ads=((self.dispX[ts]-self.dispX[ts+1])**2+(self.dispY[ts]-self.dispY[ts+1])**2)**(0.5)
                    bds.append(ads)
                    bisDist+=ads
            #Taking the standard deviation of the bisection points and of the overall trajectory, then calculating the chatter indicator from them.
            sX=statistics.stdev(bisX)
            sY=statistics.stdev(bisY)
            tX=statistics.stdev(self.dispX[w_start:w_end])
            tY=statistics.stdev(self.dispY[w_start:w_end])
            chatterIndicator=sX*sY/(tX*tY)
            self.chatsT.append(self.timeF[w_start+int(0.5*w_length)])
            #self.chatsI.append(chatterIndicator)
            self.chatsI.append(statistics.stdev(metric)**2)
            self.threshold.append(0.1)
        scaler=statistics.mean(distsTrav)
        for mm in range(len(self.chatsI)):
            self.chatsI[mm]=self.chatsI[mm]/(scaler**2)
        return [self.chatsT,self.chatsI]


    def butter_highpass(self,N, Wn): #Helper function to apply Butterworth filter to data.
        return butter(N,Wn,'high',output="sos")


    def butter_highpass_filter(self,data, N,Wn): #Function to apply Butterworth filter to data.
        sos = self.butter_highpass(N,Wn)
        y = signal.sosfilt(sos, data)
        return y
    

    def show_trajectory(self,given_time,time_window,figure_number=1):
        plt.figure(figure_number).add_subplot(projection='3d')
        w_index=0
        for i in range(len(self.timeF)):
            if self.timeF[i]>=given_time:
                w_index=i
                break
        else:
            print("Invalid time given.")
            return False
        w_length=int(self.f_sample*time_window)
        w_start=w_index
        w_end=w_start+w_length
        bisX=[] #Stores X-value of bisection points.
        bisY=[] #Stores Y-value of bisection points.
        bisT=[]
        for ts in range(w_start,w_end):
            if self.bisectionTimes[ts]:
                bisX.append(self.dispX[ts])
                bisY.append(self.dispY[ts])
                bisT.append(self.timeF[ts])
        plt.plot(self.dispX[w_start:w_end], self.dispY[w_start:w_end],self.timeF[w_start:w_end])
        plt.plot(bisX,bisY,bisT,"ro")
        plt.show()
    


    def show_raw_accelerations(self,figure_number=1):
        plt.figure(figure_number)
        plt.clf()
        plt.plot(self.timeF,self.accelX)
        plt.plot(self.timeF,self.accelY)
        plt.show()


    def show_chatter_indicators(self, figure_number=1):
        plt.figure(figure_number)
        plt.clf()
        plt.plot(self.chatsT,self.chatsI)
        plt.plot(self.chatsT,self.chatsI,"ro")
        plt.plot(self.chatsT,self.threshold)
        plt.show()
        return [self.chatsT,self.chatsI]


    def output_trajectory_gif(self,time_window=0.3,step_size=0.1):
        try:
            os.mkdir(self.filename[:-4])
        except:
            pass
        w_length=int(self.f_sample*time_window) #Calculates how many readings will be analyzed at a time.
        s_length=int(self.f_sample*step_size)
        counter=0
        for w_index in range(0,len(self.timeF)-w_length,s_length):
            plt.figure(70)
            plt.clf()
            w_start=w_index
            w_end=w_start+w_length
            bisX=[] #Stores X-value of bisection points.
            bisY=[] #Stores Y-value of bisection points.
            for ts in range(w_start,w_end):
                if self.bisectionTimes[ts]:
                    bisX.append(self.dispX[ts])
                    bisY.append(self.dispY[ts])
            plt.plot(self.dispX[w_start:w_end], self.dispY[w_start:w_end])
            plt.plot(bisX,bisY,"ro")
            plt.savefig(self.filename[:-4]+"/trajectory"+str(counter)+".png")
            counter+=1
        images = []
        filepaths=[self.filename[:-4]+"/trajectory"+str(i)+".png" for i in range(len(self.chatsT))]
        for i in filepaths:
            images.append(imageio.imread(i))
        imageio.mimsave(self.filename[:-4]+"/evolution.gif", images)