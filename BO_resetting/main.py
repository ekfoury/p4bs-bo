from measurements import *
from buffer_modifier import *
from change_detector import *
from bo import *
from global_defs import *
from utils import *

# *****************************************************
# Objects/Vars
# *****************************************************
buffer_modifier = Buffer_Modifier(junos_hostname, junos_username, junos_password)
measurements = Measurements(weight_loss=0.5, weight_delay=0.5)
bo = BO(length_scale = 0.03525, alpha = 0.000125, strategy = max_EI, kernel=RBF) #  0.000015 remove params from function call
peak_detector = real_time_peak_detection(np.zeros(lag_change), lag_change, thresh_change, influence_change, num_csv=0)
# *****************************************************

os.system('rm /home/adaptive_buffer_tuning/regrets.csv 2> /dev/null')
os.system('rm /home/adaptive_buffer_tuning/max_vals.csv 2> /dev/null')

os.system("influx delete --bucket p4bs   --start '1970-01-01T00:00:00Z' --stop $(date +\"%Y-%m-%dT%H:%M:%SZ\")")

os.system('rm *.pdf 2> /dev/null')
 
num_csv = 1

best_vals = {}
max_acqs = []

change_detection_stopping = False

while (True): 
    #if measurements.available_traffic(): 
    peak_detector.thresholding_algo(measurements.avg_F)
    if (measurements.stat_link > 98):

        if(peak_detector.change_detected() ):
        #if(not change_detection_stopping):
            change_detection_stopping = True
            print('change detected')
            bo.reset()
            regrets = []
            regret = 0
            time.sleep(1)
            stanford_buffer = compute_stanford(measurements)
            bdp_buffer = compute_BDP(measurements)
            minb, maxb = exponential_increase(bdp_buffer, measurements, buffer_modifier)
            #minb = stanford_buffer  # comment these
            #maxb = 200000           # comment these
            if(minb != -1):
                bo.update_bounds(minb, maxb)
            else:
                bo.update_bounds(stanford_buffer, maxb)
            
            print('bounds updated: ' + str(bo.bounds))

            if(len(bo.bounds) == 1):
                buffer_modifier.change_buffer(bo.bounds[0])
            else:
                acq, query_inst = bo.suggest()
                iteration = 0
                while(max(acq) > STOPPING_BO and iteration < 4):

                #while(iteration < 50):
                    #print('max(acq): ', max(acq))
                    current_buffer = query_inst[0][0]
                    current_buffer = bo.rescale_value(current_buffer)
                    print('Suggested buffer: ' + str(current_buffer))# +', ', end='')
                    previous_buffer = buffer_modifier.buffer
                    #print('Previous buffer: ' + str(previous_buffer))# +', ', end='')
                    buffer_modifier.change_buffer(current_buffer)
                    
                    if(current_buffer > 10000):
                        #print('sleeping time: ' + str(scaled_delay((current_buffer))))
                        time.sleep(scaled_delay((current_buffer)))
                    else:
                        time.sleep(1)
                        
                    if(current_buffer > previous_buffer):
                        target,_ = measurements.get_last_obj('right')
                    else:
                        target,_ = measurements.get_last_obj('left')

                    #print('F(): ' + str(target))
                    peak_detector.thresholding_algo(measurements.avg_F)
                    
                    
                    if current_buffer in best_vals:
                        best_vals[current_buffer].append(target)
                    else:
                        best_vals[current_buffer] = [target]
                    
                    bo.teach(query_inst, target)
                    iteration += 1
                    
                    
                    max_value = np.mean(best_vals[current_buffer])
                    
                    max_value_so_far = -float('inf')
                    #print(best_vals)
                    for key in best_vals.keys():
                        if(np.max(best_vals[key]) > max_value_so_far):
                            max_value_so_far = np.max(best_vals[key]) 
                            k = key
                         
                    #print('max_value:', max_value, 'key', current_buffer)
                    #print('max_value_so_far:', max_value_so_far)
                    #print('F(): ' + str(target))


                    try:
                        #if(abs(max_value - target) < 0.003):
                        #    regret += 0.0001
                        #elif (max_value > target):
                        if (max_value_so_far > target):
                            regret += (abs(target) - abs(max_value_so_far))
                    except:
                        print('except executed')
                        pass
                    #print('regret: ', regret)
                    
                    #os.system('echo '+ str(regret) +' >> /home/adaptive_buffer_tuning/regrets.csv')
                    #os.system('echo '+ str(max_value_so_far) +' >> /home/adaptive_buffer_tuning/max_vals.csv')

                    #regrets.append(regret)
                    #bo.plot_regret(regrets)
                    
                    
                    acq, query_inst = bo.suggest()
                    #bo.plot(acq, iteration)

                    max_acqs.append(max(acq))
                    #bo.plot_termination(max_acqs)

                peak_detector = real_time_peak_detection(np.zeros(lag_change), lag_change, thresh_change, influence_change, num_csv)
                num_csv += 1
                
                i=0
                objs = []
                while i < 3:
                    peak_detector.thresholding_algo(measurements.avg_F)
                    time.sleep(0.1)
                    i+=0.1

                optimal_buffer = int(bo.rescale_value(bo.optimizer.get_max()[0][0]))
                print('Stopped, optimal buffer: ' + str(optimal_buffer))
                buffer_modifier.change_buffer(optimal_buffer)
                os.system('echo '+ str(optimal_buffer) +' >> /home/adaptive_buffer_tuning/configured_buffers')

                time.sleep(1)

    else:
        buffer_modifier.change_buffer(DEFAULT_BUFFER)
        bo.reset()
    time.sleep(0.5)
