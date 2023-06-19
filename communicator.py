import RestfulAPIBase as Base

def delay():
    for i in range(100000000):
        wasteTime=1

interface=Base.RestfulInterface()
print(interface.DidInitialize())
print(interface.IsCalibrated())
if len(input())>0:
    True
interface.LoadAndRunProgram("D:/apps/STEELCUT.HWM")
print(interface.SetMaxFeedOverrides())
if len(input())>0:
    True
interface.Shutdown()
print("All Done")