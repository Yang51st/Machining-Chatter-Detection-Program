import ChatterDetector as ChatterDetector

detector=ChatterDetector.ChatterDetector()
detector.ConnectMachine()
POINTS_TO_COLLECT=8
for ptc in range(1):
    detector.RecordCut()
detector.MachineShutdown()
detector.CreateStabilityLobe()