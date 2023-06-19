import csv

times=[]
col1=[]
col2=[]
with open("VibrationData/ChatterIndicatorTests/PCBData.csv",mode="r") as file:
    csvFile = csv.reader(file)
    for lines in csvFile:
        times.append(float(lines[0]))
        col1.append(float(lines[1]))
        col2.append(float(lines[2]))

filename="VibrationData/ChatterIndicatorTests/PCBData.csv"
with open(filename, 'w',newline="") as csvfile:
    csvwriter = csv.writer(csvfile)
    for reading in range(len(times)):
        csvwriter.writerow([times[reading]-times[0],col1[reading],col2[reading]])
