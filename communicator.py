"""import RestfulAPIBase as Base

interface=Base.RestfulInterface()
interface.DidInitialize()
interface.IsCalibrated()
#interface.LoadAndRunProgram("D:/apps/SpindleSpeedChange.HWM")
interface.GetMachinePositionX()
interface.GetSpindleSpeed()
interface.Shutdown()"""

import serialTest as SerialConnection

detector=SerialConnection.ChatterDetector()
detector.ConnectDAQ()
detector.StartChatterMonitor()
"""for k in range(1000):
    print(detector.interface.GetSpindleOrientation())"""
detector.interface.Shutdown()
# 127394.55395507812 - 127394.04077148438
# 0.5 per rotation?