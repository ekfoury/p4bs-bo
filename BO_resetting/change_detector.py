import numpy as np
import time
import os

class real_time_peak_detection():
    def __init__(self, array, lag, threshold, influence, num_csv, filepath='/home/adaptive_buffer_tuning/BO_resetting/change_detection_'):
        self.y = list(array)
        self.length = len(self.y)
        self.lag = lag
        self.threshold = threshold
        self.influence = influence
        self.signals = [0] * len(self.y)
        self.filteredY = np.array(self.y).tolist()
        self.avgFilter = [0] * len(self.y)
        self.stdFilter = [0] * len(self.y)
        self.avgFilter[self.lag - 1] = np.mean(self.y[0:self.lag]).tolist()
        self.stdFilter[self.lag - 1] = np.std(self.y[0:self.lag]).tolist()
        self.filepath = filepath +str(num_csv)+'.csv'
        os.system("echo y, signals, filteredY, avgFilter, stdFilter" + '>' + self.filepath)
        
    def print_to_file(self):
        i = len(self.y) - 1
        os.system("echo " + str(time.time()) +',' + str(self.y[i]) +',' + str(self.signals[i]) + ',' + str(self.filteredY[i]) +',' + str(self.avgFilter[i]) + ',' + str(self.stdFilter[i]) + '>>' + self.filepath)
        
    
    def thresholding_algo(self, new_value):
        self.y.append(new_value)
        i = len(self.y) - 1
        self.length = len(self.y)
        #print(i)
        if i < self.lag:
            return 0
        elif i == self.lag:
            self.signals = [0] * len(self.y)
            self.filteredY = np.array(self.y).tolist()
            self.avgFilter = [0] * len(self.y)
            self.stdFilter = [0] * len(self.y)
            self.avgFilter[self.lag] = np.mean(self.y[0:self.lag]).tolist()
            self.stdFilter[self.lag] = np.std(self.y[0:self.lag]).tolist()
            return 0

        self.signals += [0]
        self.filteredY += [0]
        self.avgFilter += [0]
        self.stdFilter += [0]
        #print ('self.y[i] - self.avgFilter[i - 1]: ' + str(self.y[i] - self.avgFilter[i - 1]))
        #print ('self.threshold * self.stdFilter[i - 1]: ' + str(self.threshold * self.stdFilter[i - 1]))

        if abs(self.y[i] - self.avgFilter[i - 1]) > self.threshold * self.stdFilter[i - 1]:
            
            if self.y[i] > self.avgFilter[i - 1]:
                self.signals[i] = 1
            else:
                self.signals[i] = -1

            self.filteredY[i] = self.influence * self.y[i] + (1 - self.influence) * self.filteredY[i - 1]
            self.avgFilter[i] = np.mean(self.filteredY[(i - self.lag):i])
            self.stdFilter[i] = np.std(self.filteredY[(i - self.lag):i])
            
        else:
            self.signals[i] = 0
            self.filteredY[i] = self.y[i]
            self.avgFilter[i] = np.mean(self.filteredY[(i - self.lag):i])
            self.stdFilter[i] = np.std(self.filteredY[(i - self.lag):i])

        self.print_to_file()
        return self.signals[i]


    def change_detected(self):
        return self.signals[len(self.signals) - 1] != 0 #and self.signals[len(self.signals) - 2] != 0
