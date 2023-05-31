import os
import sys
import math
from os import system
import subprocess
import time
import threading
import jnpr
import socket




MAXIMUM_BUFFER = 200000
p4 = bfrt.p4bs.pipe
prev_N = 0
long_flows = {}
SRTT = 0
SRTT_bscl = 0
avg_rtt = 0
ALPHA = 0.8
#BW=1000000000
BW=500000000
prev_rtt=0
prev_rtt_bscl=0
q_hat = 0.5 # 200ms
avg_q = 0 
prev_avg_q = 0
loss_rate_hat_headroom = 0.00525
loss_rate_hat = 0.010 - loss_rate_hat_headroom# 2%
SRTT_CHANGE_THRESHOLD = 0.15
B_max = BW * q_hat / 8 # Maximum buffer size in bytes
B_min = 0
bs_minimum = 0
bs_maximum = B_max
prev_temporal  = 0
prev_buffer_for_bscl_percent = 0
prev_total_sent_before = -1
prev_total_sent_after = -1
iteration=0
prev_bytes_counter = 0
recalculate=False
found=False
total_sent = 0
total_retr = 0
avg_link_util = 0
avg_tput = 0
avg_loss_rate = 0
buffer = 0
last_saved_SRTT = 0
new_flow=False
r = BW * 0.0025 / 1000
N = 0
prev_buffer = 0
total_sent_before = 0
total_sent_after = 0
updating_B_min = False
prev_total_sent = -1
prev_total_retr = -1
buffer_change_source = None
is_searching=False

MAX_QUEUE_DELAY=200         #<---- customize this
MAX_QUEUE_DELAY=MAX_QUEUE_DELAY * 1000
os.system("/home/p4bs/bfrt_python/./set_buffer.sh 20000")



with open('/home/p4bs/bw.txt') as f:
    lines = f.readlines()

BW = int(lines[0])

def compute_stanford():
    global N
    if (N > 0):
        import math
        global prev_rtt
        global SRTT
        global BW
        C = BW / 8 # convert to bytes
        buffer = SRTT * C
        return math.ceil(buffer / math.sqrt(N)) 
    return 0


# This should be invoked whenever N or SRTT change drastically
def update_B_min():
    import math
    global is_searching
    global B_min
    global B_max
    global bs
    global bs_minimum
    global bs_maximum
    global recalculate
    global compute_stanford
    global buffer
    global N
    global new_flow
    global change_buffer
    import threading
    global MAXIMUM_BUFFER
    global updating_B_min
    global prev_loss
    global prev_avg_q
    import time
    global buffer_change_source
    global control_sock
    sent = False
    #while (not sent):
    while (1):
        prev_B_min = B_min
        tmp_B_min = compute_stanford()
        
        if(abs(tmp_B_min - prev_B_min) > 0.5 * prev_B_min):#0.8 * prev_B_min):# or new_flow ==  True:       
            print('Lower bound buffer updated')
            B_min = compute_stanford()
            prev_B_min = B_min
            #if(B_min != 0):
                #control_sock.send(str('bmin_update_' + str(str(int(int(B_min) * 8 / 1e3)) + '_' + str(int(int(B_min) * 8 / 1e3) * math.sqrt(N)))).encode())
            #sent = True
        time.sleep(0.4)
        

def new_long_flow(dev_id, pipe_id, direction, parser_id, session, msg):
    global p4
    global long_flows
    #try:
    for digest in msg:
        long_flows[digest['rev_flow_id']] = 0
        p4.Ingress.counted_flow.add_with_meter(flow_id=digest['flow_id'], ENTRY_TTL = 1000)
        #long_flows += 1
#except:
    #    pass
    return 0
 
def long_flow_timeout(dev_id, pipe_id, direction, parser_id, entry):
    global p4
    global long_flows
    try:
        flow_id = entry.key[b'meta.flow_id']
        del long_flows[flow_id]
        if(len(long_flows) == 0):
            p4.Ingress.counted_flow.clear()
            p4.Ingress.sketch0.clear()
            p4.Ingress.sketch1.clear()
            p4.Ingress.sketch2.clear()
            p4.Ingress.sketch3.clear()
    except Exception as e:
            print(e)
'''
def new_long_flow(dev_id, pipe_id, direction, parser_id, session, msg):
    global p4
    global long_flows
    global recalculate
    try:    
        for digest in msg:
            long_flows[digest['rev_flow_id']] = 0
            p4.Ingress.informed_long_flows.mod(REGISTER_INDEX=digest['flow_id'], f1 =1)
        new_flow = True
        #print('new_long_flow')
        #update_B_min()
    except:
        return 0
    return 0



def long_flow_timeout(dev_id, pipe_id, direction, parser_id, entry):
    try:
        global p4
        global long_flows
        global update_B_min
        global prev_N
        flow_id = entry.key[b'meta.flow_id']
        if flow_id in long_flows:
            p4.Ingress.informed_long_flows.mod(REGISTER_INDEX=flow_id, f1 =0)
            del long_flows[flow_id]
            entry.remove()
            #update_B_min()
    except:
        return 0
   
'''

def update_srtt():
    import time
    while (1):
        if(len(long_flows) >  0):
            long_flows_copy = long_flows.copy()
            import math
            global prev_rtt
            global SRTT
            global SRTT_CHANGE_THRESHOLD
            global last_saved_SRTT
            sum = 0
            for key, value in long_flows_copy.items():
                #print(long_flows[key])
                if(float(long_flows_copy[key]) < 100000000):
                    sum += (float(long_flows_copy[key]) / 1e9)
            
            avg_rtt = sum / len(long_flows_copy)
            ALPHA = 0.875
            if(prev_rtt == 0):
                prev_rtt = avg_rtt

            if (SRTT != 0):
                SRTT = ALPHA * SRTT + (1-ALPHA) * avg_rtt
            else:
                SRTT = avg_rtt
                
            prev_rtt = SRTT
            #print('SRTT: ' + str(SRTT))
        else:
            SRTT=0
            prev_rtt=0
        time.sleep(0.1)
   
def rtt_sample(dev_id, pipe_id, direction, parser_id, session, msg):
    global p4
    global rtts
    global long_flows
    global update_srtt
    for digest in msg:
        
        if digest['flow_id'] in long_flows:
            #print(digest['rtt'])
            long_flows[digest['flow_id']]  = str(digest['rtt'])
    #update_srtt()
    return 0

def queue_delay_sample():
    global p4
    import time
    global avg_q
    global prev_avg_q
    prev_q = 0
    count_same = 0
    queue_delay = 0
    while (1):
        previous_sample = queue_delay        
        queue_delay = p4.Egress.queue_delays.get(REGISTER_INDEX=0, from_hw=True, print_ents=False).data[b'Egress.queue_delays.f1'][1]
        queue_delay = (queue_delay) / (200000000)
        if(queue_delay == 0):
            avg_q = 0
            continue
        #print('previous: ' + str(previous_sample))
        #print('current: ' + str(queue_delay))
        
        if(queue_delay == previous_sample):
            avg_q = 0
        else:
            avg_q = queue_delay
    
        time.sleep(0.1)
    return 0



def calc_link_util():
    global prev_bytes_counter
    global p4
    global avg_link_util
    global avg_tput
    global BW
    import time
    while (1):
        link_util_result=0
        new_bytes_counter = p4.Ingress.link_stats.get(COUNTER_INDEX=0, print_ents=False, from_hw=True).data[b'$COUNTER_SPEC_BYTES']
        link_util = (new_bytes_counter - prev_bytes_counter) * 8
        if(link_util < 0):
            link_util = 0
        if(link_util != 0):
            if(link_util/BW * 100 > 100):
                link_util_result = 100
            else:
                link_util_result = link_util/(BW) * 100
        prev_bytes_counter = new_bytes_counter
        
        ALPHA = 0.2
        if (avg_link_util != 0):
            avg_link_util = ALPHA * avg_link_util + (1-ALPHA) * link_util_result
            avg_tput = ALPHA * avg_tput + (1-ALPHA) * link_util
        else:
            avg_link_util = link_util_result
            avg_tput = link_util
        time.sleep(1)
       


def calc_loss_rate():    #<---- based on retransmissions
    global p4
    global prev_total_sent
    global prev_total_retr
    global total_sent
    global total_retr
    global avg_loss_rate
    import time
    global is_searching
    global avg_link_util
    
    from datetime import datetime
    os.system('echo "" > /home/p4bs/stats_loss.csv')
    i=0
    tt=0
    while(1):
        rate = 0
        total_sent = float(p4.Ingress.total_sent.get(REGISTER_INDEX=0, from_hw=True, print_ents=False).data[b'Ingress.total_sent.f1'][1])
        total_retr = float(p4.Ingress.total_retr.get(REGISTER_INDEX=0, from_hw=True, print_ents=False).data[b'Ingress.total_retr.f1'][1])
        #print('total_sent: ', total_sent)
        tt+=total_retr - prev_total_retr
        if(i%10 ==0 and i > 0):
            #print('total_retr: ', tt)
            os.system("echo " + str(datetime.now().timestamp()) + ',' + str(tt) + " >> /home/p4bs/stats_loss.csv")
            tt=0
        i+=1
        if(prev_total_sent == -1):
            prev_total_sent = total_sent
        if(prev_total_retr == -1):
            prev_total_retr = total_retr
        if (total_sent - prev_total_sent != 0):
            rate = ((total_retr - prev_total_retr) / (total_sent - prev_total_sent) ) 
        
        if(avg_link_util < 90):
            avg_loss_rate = 0
            prev_total_sent = -1
            prev_total_retr = -1
        else:
            rate = rate * 1.4
            
            if(avg_loss_rate < 0):
                avg_loss_rate = 0
            
            ALPHA = 0.8
            if (avg_loss_rate != 0):
                avg_loss_rate = ALPHA * avg_loss_rate+ (1-ALPHA) * rate
            else:
                avg_loss_rate = rate
                                        
            prev_total_sent = total_sent 
            prev_total_retr = total_retr
            
        time.sleep(0.1)
        #time.sleep(0.5)
        
prev_total_before = -1
prev_total_after = -1
prev_rate = - 1
total_before=0
total_after=0

def reset_sketches():
    global p4
    import time
    global long_flows
    
    while (True):
        time.sleep(4)
        #long_flows.clear()
        p4.Ingress.sketch0.clear()
        p4.Ingress.sketch1.clear()
        p4.Ingress.sketch2.clear()
        p4.Ingress.sketch3.clear()
        

def calc_loss_rate_results():    
    global p4
    global prev_total_before
    global prev_total_after
    global avg_loss_rate
    global prev_rate
    global total_after
    global total_before
    import time
    import subprocess
    while(1):
        try:
            
            rate = 0
            output = subprocess.check_output("/root/bf-sde-9.4.0/./run_bfshell.sh --no-status-srv -i -f  /home/p4bs/get_counts.sh | tail -n 4 | head -n 2 | awk -F\| '{print $13}' | sed 's/\s*//g'", shell=True)
            output_str = str(output.decode())
            total_after = int(output_str.split('\n')[0]) 
            total_before = int(output_str.split('\n')[1])

            
            if(prev_total_before == -1):
                prev_total_before = total_before
            if(prev_total_after == -1):
                prev_total_after = total_after 

            if (total_after - prev_total_after != 0):
                #print(total_after - total_before)
                #print(packets)
                current_buffer = float(subprocess.check_output("cat /home/p4bs/buffer_current", shell=True))
                
                #packets = (current_buffer * 25000000 / 200000) / 1500
                #total_after + packets

                if(current_buffer > 100000):
                    rate = (-1 + ((total_before - prev_total_before) / (total_after - prev_total_after + 16666)))
                else:
                    rate = (-1 + ((total_before - prev_total_before) / (total_after - prev_total_after)))

                if(rate < 0):
                    rate = 0
                    
                ALPHA = 0.4
                if (avg_loss_rate != 0):
                    avg_loss_rate = ALPHA * avg_loss_rate+ (1-ALPHA) * rate
                else:
                    avg_loss_rate = rate

                prev_total_before = total_before
                prev_total_after = total_after 
            else:
                avg_loss_rate = 0
            
            time.sleep(0.1)
        except Exception as e:
            print(e)
            pass
            
        

def calc_loss_rate2(dev_id, pipe_id, direction, parser_id, session, msg):    #<---- based on report
    global p4
    global prev_total_before
    global prev_total_after
    global avg_loss_rate
    global prev_rate
    global total_after
    global total_before
    
    losses = []
    for digest in msg:
        #print(digest)
        #print(str(digest['before']) + '_' + str(digest['after']))
        
        #total_before = float(str(digest['before'])) 
        #total_after = float(str(digest['after'])) 
        #print(total_before,total_after)
        
        #total_before = float(str(digest['before'])) 
        #total_after = float(str(digest['after'])) 
        '''
        if(prev_total_before == -1):
            prev_total_before = total_before
        if(prev_total_after == -1):
            prev_total_after = total_after 
            
        if (total_after - prev_total_after != 0):
            print(total_after - total_before)
            rate = (-1 + ((total_before - prev_total_before) / (total_after - prev_total_after + 166)))
            
            if(prev_rate == -1 ):
                prev_rate = rate

            if(rate == prev_rate):
                rate = 0
            
            prev_rate = rate
            if (rate < 0.0):
                rate = 0.0
            
            #losses.append(rate)
            
            prev_total_before = total_before
            prev_total_after = total_after
            
            
            ALPHA = 0.225
            if (avg_loss_rate != 0):
                avg_loss_rate = ALPHA * avg_loss_rate+ (1-ALPHA) * rate
            else:
                avg_loss_rate = rate
        else:
            avg_loss_rate = 0
      
        '''
    return 0

def get_N():
    import time
    global N
    global prev_N
    global recalculate
    global long_flows
    while(1):  
        #print(N)
        N = len(long_flows)
        time.sleep(1)
        
try:
    #p4.Ingress.metering.idle_table_set_notify(enable=True, callback=long_flow_timeout, interval=200, min_ttl=400, max_ttl=1000)
    #p4.IngressDeparser.new_flow_digest.callback_register(new_flow_f)
    p4.Ingress.counted_flow.idle_table_set_notify(enable=True, callback=long_flow_timeout, interval=500, min_ttl=400, max_ttl=1000)
    p4.IngressDeparser.new_long_flow_digest.callback_register(new_long_flow)
    p4.IngressDeparser.rtt_sample_digest.callback_register(rtt_sample)
    p4.IngressDeparser.before_after.callback_register(calc_loss_rate2)
    p4.Egress.lpf_queue_delay_1.add(0, 'SAMPLE', 1000000, 1000000, 0)
except:
    print('Error registering callback')
    
weight_loss = 0.5#0.9
weight_delay = 0.5#0.1
prev_loss = 0
prev_q = 0
prev_obj_function_value=0
last_loss_used=10
last_q_used=0



def evaluate_objective_function(direction):
    import time
    global avg_loss_rate
    global avg_q
    global weight_loss
    global weight_delay
    global prev_loss
    global prev_q 
    
        
    obj_function_value=0

    i = 0
    
    while(i < 10000):
        
        tmp_avg_loss_rate = avg_loss_rate / 0.05
        tmp_avg_q = avg_q
        
        
            
            
        if(direction == 'left'):
            #print('left')
            #print('tmp_avg_q: ' + str(tmp_avg_q) +' prev_q: ' + str(prev_q))
            if(tmp_avg_q < prev_q and tmp_avg_loss_rate >= prev_loss):
                obj_function_value = (weight_loss) * tmp_avg_loss_rate + (weight_delay) * tmp_avg_q
                prev_q = tmp_avg_q
                prev_loss = tmp_avg_loss_rate
                if(obj_function_value < 1e-4):
                    obj_function_value=0                
                return obj_function_value
        elif (direction == 'right'):
            #print('right')
            #print('tmp_avg_q: ' + str(tmp_avg_q) +' prev_q: ' + str(prev_q))
            if(tmp_avg_q > prev_q and tmp_avg_loss_rate < prev_loss):
                obj_function_value = (weight_loss) * tmp_avg_loss_rate + (weight_delay) * tmp_avg_q
                prev_q = tmp_avg_q
                prev_loss = tmp_avg_loss_rate
                if(obj_function_value < 1e-4):
                    obj_function_value=0                
                return obj_function_value
        else:
            obj_function_value = (weight_loss) * tmp_avg_loss_rate + (weight_delay) * tmp_avg_q
            prev_q = tmp_avg_q
            prev_loss = tmp_avg_loss_rate
            if(obj_function_value < 1e-4):
                obj_function_value=0                
            return obj_function_value
        i+=1
        #time.sleep(0.1)
    #print(i)
    obj_function_value = (weight_loss) * tmp_avg_loss_rate + (weight_delay) * tmp_avg_q
    if(prev_q == 0):
        prev_q = tmp_avg_q
    if(prev_loss == 0):
        prev_loss = tmp_avg_loss_rate
    if(obj_function_value < 1e-4):
        obj_function_value=0                
    return obj_function_value
    
    
calc_link_util_thread = threading.Thread(target=calc_link_util, name="calc_link_util")
calc_loss_rate_thread = threading.Thread(target=calc_loss_rate, name="calc_loss_rate")
calc_queue_delay_thread = threading.Thread(target=queue_delay_sample, name="queue_delay_sample")
get_N_thread = threading.Thread(target=get_N, name="get_N")
update_srtt_thread = threading.Thread(target=update_srtt, name="update_srtt")
#calc_loss_rate_results_thread = threading.Thread(target=calc_loss_rate_results, name="calc_loss_rate_results")
#update_B_min_thread = threading.Thread(target=update_B_min, name="update_B_min")
periodic_reset = threading.Thread(target=reset_sketches, name="reset_sketches")

calc_link_util_thread.start()
calc_loss_rate_thread.start()
calc_queue_delay_thread.start()
get_N_thread.start()
periodic_reset.start()
#calc_loss_rate_results_thread.start()
#update_B_min_thread.start()
update_srtt_thread.start()

os.system("echo "" > test_buffers")
last_good_buffer = 0
bs = False
print ("   N  |     Throughput  |    Link utilization  |   Loss rate  |     RTT  |    Current Buffer")
print ('--------------------------------------------------------------------------------------------')

def get_last_obj(direction):
    import statistics
    global evaluate_objective_function
    global avg_q
    global avg_loss_rate
    import time
    obj_function_values = []
    loss_values = []
    all_obj_func = []
    all_loss = []
    j = 0
    all_obj_func.clear()
    all_loss.clear()
    
    #avg_q = 0
    #avg_loss_rate = 0
    
    while (j < 10):
        i = 0
        obj_function_values.clear()
        while (i < 10):
            obj_function_value_i = evaluate_objective_function(direction)
            loss_values.append(avg_loss_rate)
            obj_function_values.append(obj_function_value_i)
            
            #time.sleep(0.1)
            i+=1
        obj_func = statistics.mean(obj_function_values)#[8000:10000])
        loss_result = statistics.mean(loss_values)#[8000:10000])
        print(str(obj_func) +', ' + str(loss_result))
        time.sleep(0.05)
        all_obj_func.append(obj_func)
        all_loss.append(loss_result)
        j+=1
    #obj_func_final = statistics.mean(all_obj_func)
    obj_func_final = statistics.mean(all_obj_func)
    loss_final = statistics.mean(all_loss)
    print('obj_func_final: ' + str(obj_func_final) + ', loss_final: ' + str(loss_final))    
    return obj_func_final,loss_final

'''
    i=0
    updated = update_B_min()
    if(N > 0 and updated):
        #sock.send(str('start_sending').encode())
        msg = sock.recv(1024)

        msg = msg.decode()
        #print('msg received')
        if ("buffer_" in msg):
            obj_function_values.clear()
            buffer = float(str(msg.split("_")[1]))
            while(i<10000):
                obj_function_value_i = evaluate_objective_function()
                obj_function_values.append(obj_function_value_i)
                i+=1
            obj_func = statistics.median(obj_function_values)
            if(obj_func != 0):
                #print('here')
                sock.send(str('obj_func_' + str(obj_func)).encode())

        #print(str(obj_function_value_i), str(avg_loss_rate), str(avg_q))
        
        
        time.sleep(0.1)
        update_B_min()
    '''



sock = socket.socket()         # Create a socket object
host = socket.gethostname()    # Get local machine name
#host = '10.173.85.15' #socket.gethostname()    # Get local machine name
port = 60002                   # Reserve a port for your service.
sock.connect((host, port))

weight_loss  = 0.5
weight_delay = 0.5


last_buffer = 0

import json

current_buffer = 0

i=0
while(1):
    
    try:
        with open('/home/p4bs/current_buffer') as f:
            lines = f.read()
            current_buffer = int(lines)
            f.close()
    except Exception as e:
        print(e)
        
    with open('/home/p4bs/bw.txt') as f:
        lines = f.readlines()

    BW = int(lines[0])

    #print(current_buffer)
    #counted_flow_info = p4.Ingress.counted_flow.info(print_info=False, return_info=True)
    #print('counted_flow_usage: ', str(counted_flow_info['usage']))

    stat_SRTT = "{:.4f}".format(SRTT)
    stat_LOSS = "{:.4f}".format(avg_loss_rate)
    stat_Q = "{:.4f}".format(avg_q)
    stat_LINK = "{:.4f}".format(avg_link_util)
    F = "{:.4f}".format((weight_loss) * float(stat_LOSS) / 0.05 + (weight_delay) * float(stat_Q))
    
    if((float(stat_Q) == 0) or N == 0):
        #print(i)
        i+=1
    else:
        i=0
    
    '''
    if((weight_loss) * float(stat_LOSS) + (weight_delay) * float(stat_Q) == 0):
        i+=1
    else:
        i=0
    '''
    if(i==100): #10):
        try:
            i=0
            long_flows.clear()
            prev_rtt = 0
            SRTT = 0
            
            #p4.Egress.lpf_queue_delay_1.clear()
            #p4.Egress.lpf_queue_delay_2.clear()    
            p4.Ingress.calc_flow_id.clear() 
            prev_total_before = -1
            prev_total_after = -1
            avg_loss_rate = 0
            p4.Ingress.calc_rev_flow_id.clear()    
            p4.Ingress.copy32_1.clear()    
            p4.Ingress.copy32_2.clear()    
            p4.Ingress.crc16_1.clear()    
            p4.Ingress.crc16_2.clear()    
            p4.Ingress.crc32_1.clear()    
            p4.Ingress.crc32_2.clear()    
            #p4.Ingress.informed_long_flows.clear()    
            p4.Ingress.last_seq.clear()    
            p4.Ingress.link_stats.clear()    
            #p4.Ingress.metering.clear()    
            p4.Ingress.reg_table_1.clear()    
            p4.Ingress.rev_hash.clear()    
            #p4.Ingress.store_and_check_if_long_flow_informed.clear()    
            p4.Ingress.total_retr.clear()    
            p4.Ingress.total_sent.clear()    
            
            long_flows.clear()
            p4.Ingress.sketch0.clear()
            p4.Ingress.sketch1.clear()
            p4.Ingress.sketch2.clear()
            p4.Ingress.sketch3.clear()
            #p4.counted_flow.clear()
            

        except Exception as e:
            print(e)
            pass
    
    if(current_buffer/200000 > float(stat_Q)):
        print('N: ' + str(N) + '\tSRTT: ' + 
        str(stat_SRTT) + '\tLoss: ' + str(stat_LOSS) + '\tQ: ' + str(stat_Q) + '\tLink: ' + str(stat_LINK) +'\tF(): ' + str(F))

        stats = str(N) + '_' + str(stat_SRTT) + '_' + str(stat_LOSS) + '_' + str(stat_Q) + '_' + str(stat_LINK) + '_' + str(F)
        #print(stats)
        sock.send(stats.encode())
        
    time.sleep(0.1)

sock.close()                     # Close the socket when done

