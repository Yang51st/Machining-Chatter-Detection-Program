from Chatter import ChatterDetectionUtils
import matplotlib.pyplot as plt
from ChatterAutoEncoder import ChatterAutoEncoder


filename="EBI_Roland_Good_Cutter/60003.csv"
ChatterHelper=ChatterDetectionUtils(filename,spindle_speed=6000,column_order="TZXY")
chatsT,chatsI=ChatterHelper.calculate_chatter_indicator(time_window=0.3,step_size=0.1)
#CI_Series=ChatterHelper.show_chatter_indicators(figure_number=1)
#ChatterHelper.show_raw_accelerations(figure_number=2)
#ChatterHelper.show_trajectory(given_time=6.9,time_window=0.3,figure_number=3)
#ChatterHelper.output_trajectory_gif(time_window=0.3, step_size=0.1)
CAE=ChatterAutoEncoder()
CAE.load_data(filename,"TZXY",200)
CAE.predict_chatter(0.10)
lossV=CAE.plot_chatter()
print(lossV)


figs,axes=plt.subplots(3)
figs.suptitle("Roland Good Cutter at 6000 RPM Graph3")
plt.tight_layout()
axes[0].plot(ChatterHelper.timeF,ChatterHelper.accelX)
axes[0].plot(ChatterHelper.timeF,ChatterHelper.accelY)
axes[0].set_title("Acceleration Time Series")
axes[0].set_ylabel("Acceleration (m/s^2)")
axes[0].set_xlabel("Time (s)")
axes[1].plot(chatsT,chatsI)
axes[1].plot(chatsT,ChatterHelper.threshold)
axes[1].set_title("Modified Chatter Indicator Time Series")
axes[1].set_ylabel("Unitless")
axes[1].set_xlabel("Time (s)")
axes[2].plot(ChatterHelper.timeF,lossV[:-1])
axes[2].plot(chatsT,[1 for _ in range(len(chatsT))])
axes[2].set_title("Loss Time Series")
axes[2].set_yscale("log")
axes[2].set_ylabel("Unitless")
axes[2].set_xlabel("Time (s)")
plt.show()