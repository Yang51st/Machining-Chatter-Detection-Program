import csv

filename="VibrationData/HurcoVMX42SRTi/SKF_F18IN_T25_D0p125IN_3000RPM_5A_EBI_ON_TABLE.csv"
times=[]
col1=[]
col2=[]
with open(filename,mode="r") as file:
    csvFile = csv.reader(file)
    for lines in csvFile:
        times.append(float(lines[0]))
        col1.append(float(lines[1]))
        col2.append(float(lines[2]))

with open(filename,'w',newline="") as csvfile:
    csvwriter = csv.writer(csvfile)
    for reading in range(len(times)):
        csvwriter.writerow([times[reading]-times[0],col1[reading],col2[reading]])
