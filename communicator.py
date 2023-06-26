import serialTest as SerialConnection

detector=SerialConnection.ChatterDetector()
detector.ConnectDAQ()
detector.GetMachineSettings()
POINTS_TO_COLLECT=10
for ptc in range(len(POINTS_TO_COLLECT)):
    detector.RecordCut()
detector.CreateStabilityLobe()
detector.DetectorShutdown()