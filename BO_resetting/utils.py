from global_defs import *

def exponential_increase(buffer, measurements, buffer_modifier):   
    buffer = int(buffer)
    if (measurements.stat_LOSS <= THRESH_LOSS_EXPONENTIAL_INCREASE): #0.001
        return -1, buffer
    if (measurements.stat_LOSS >= 0.03): #0.001
        return compute_BDP(measurements), MAXIMUM_BUFFER/2
    else:
        while(measurements.stat_LOSS > THRESH_LOSS_EXPONENTIAL_INCREASE): #0.001
            if(buffer == 0):
                return -1, 0
            print('exponential_increase')
            buffer = buffer * 2
            if (buffer >= MAXIMUM_BUFFER):
                buffer = MAXIMUM_BUFFER
                break
                
            buffer_modifier.change_buffer(buffer)
            time.sleep(1)
    return -1, buffer


def compute_BDP(measurements):
    buffer = measurements.stat_SRTT * 1000 * 1000
    if(buffer > MAXIMUM_BUFFER):
        buffer = MAXIMUM_BUFFER
    if (buffer == 0):
        return MINIMUM_BUFFER
    return buffer
    
def compute_stanford(measurements):
    if (measurements.N != 0):
        buffer = compute_BDP(measurements) 
        return int(math.ceil(buffer / math.sqrt(measurements.N))) 
    return MINIMUM_BUFFER
    
def scaled_delay(x):
    MAX = 3.5 #2.5
    MIN = 1 #1
    return (MAX - MIN) * ((x - int(MINIMUM_BUFFER))/(MAXIMUM_BUFFER - int(MINIMUM_BUFFER))) + MIN
