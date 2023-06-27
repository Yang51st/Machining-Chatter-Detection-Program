import ChatterDetector as ChatterDetector

detector=ChatterDetector.ChatterDetector()
detector.ConnectMachine()
POINTS_TO_COLLECT=8
for ptc in range(POINTS_TO_COLLECT):
    input("Enter any key to begin. Make sure spindle is spinning.")
    detector.RecordCut()
detector.MachineShutdown()
detector.CreateStabilityLobe()