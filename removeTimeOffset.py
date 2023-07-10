import csv

filename="VibrationData/PerfectoD1/DoF_XRail_YRail.csv"
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
