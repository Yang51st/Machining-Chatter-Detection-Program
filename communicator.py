import ChatterDetector as CD

detector=CD.ChatterDetector()
detector.ConnectMachine()
POINTS_TO_COLLECT=8
while len(detector.lobeRPM)<POINTS_TO_COLLECT:
    print(detector.lobeDepth)
    print(detector.lobeRPM)
    detector.RecordCut()
detector.MachineShutdown()
detector.CreateStabilityLobe()