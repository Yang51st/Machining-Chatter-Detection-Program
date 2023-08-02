import os
import csv
# assign directory
directory = "VibrationData/HurcoVMX42SRTi/CutsAlongX/UnalignedData"
 
# iterate over files in
# that directory
for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    # checking if it is a file
    if os.path.isfile(f):
        times=[]
        col1=[]
        col2=[]
        col3=[]
        with open(f,mode="r") as file:
            csvFile = csv.reader(file)
            for lines in csvFile:
                times.append(float(lines[0]))
                col1.append(float(lines[1]))
                col2.append(float(lines[2]))
                col3.append(float(lines[3]))
        with open(f,'w',newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            for reading in range(len(times)):
                if reading==0:
                    csvwriter.writerow(["Time (s)","Accel X (m/s^2)","Accel Y (m/s^2)","Accel Z (m/s^2)"])
                csvwriter.writerow([times[reading]-times[0],col3[reading]/1000,col1[reading]/1000,col2[reading]/1000])