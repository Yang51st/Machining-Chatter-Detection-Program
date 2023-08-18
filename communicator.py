import ChatterDetector as CD
#D0.05IN for first batch.
detector=CD.ChatterDetector()
detector.ConnectMachine()
POINTS_TO_COLLECT=8
while len(detector.lobeRPM)<POINTS_TO_COLLECT:
    print(detector.lobeDepth)
    print(detector.lobeRPM)
    detector.RecordCut()
detector.MachineShutdown()
detector.CreateStabilityLobe()