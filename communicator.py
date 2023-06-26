import ChatterDetector as ChatterDetector

detector=ChatterDetector.ChatterDetector()
"""
detector.ConnectMachine()
detector.ConnectDAQ()
detector.GetMachineSettings()
POINTS_TO_COLLECT=8
for ptc in range(len(POINTS_TO_COLLECT)):
    input("Enter Any Key to Begin")
    detector.RecordCut()
"""
detector.CreateStabilityLobe()
#detector.DetectorShutdown()