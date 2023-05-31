import socket
import threading
import time
import statistics
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


class Measurements():
    def __init__(self, weight_loss=0.5, weight_delay=0.5):
        self.N = 0
        self.stat_LOSS = 0
        self.stat_SRTT = 0
        self.stat_Q = 0
        self.stat_F = 0
        self.weight_loss = weight_loss
        self.weight_delay = weight_delay
        self.avg_F = 0
        self.stat_link = 0
        
        ## Grafana Plotting below
        token = "INSERT_HERE"
        org = "INSERT_HERE"
        url = "INSERT_HERE"
        client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
        self.bucket="p4bs"
        self.write_api = client.write_api(write_options=SYNCHRONOUS)
        
        self._init_socket()



    def _init_socket(self, host = socket.gethostname(), port = 60002):
        sock = socket.socket()         # Create a socket object
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))        # Bind to the port
        print('*'*60)
        print('Waiting for connection from the P4 switch...')
        sock.listen(5)                 # Now wait for client connection.
        self.c, addr = sock.accept()     # Establish connection with client.
        print('Connected!')
        print('*'*60)
        print('\n')
        self.start_measurements_thread()

    def start_measurements_thread(self):
        collect_measurements_thread = threading.Thread(target=self.collect_measurements, name="collect_measurements")
        collect_measurements_thread.start()


    def collect_measurements(self):
        while (1):
            measurements = self.c.recv(1024)
            measurements = measurements.decode()            
            self.N = int(measurements.split('_')[0])
            self.stat_SRTT = float(measurements.split('_')[1])
            self.stat_LOSS = float(measurements.split('_')[2])
            self.stat_Q = float(measurements.split('_')[3])
            self.stat_link = float(measurements.split('_')[4])
            self.stat_F = float(measurements.split('_')[5])
            self.update_F()
            point_rtt = (
                Point("rtts")
                .tag("tagname1", "tagvalue1")
                .field("rtt", float(self.stat_SRTT))
              )
            self.write_api.write(bucket=self.bucket, org="cilab", record=point_rtt)
            point_queue = (
                Point("queues")
                .tag("tagname1", "tagvalue1")
                .field("queue", float(self.stat_Q))
              )
            self.write_api.write(bucket=self.bucket, org="cilab", record=point_queue)
            
            point_loss = (
                Point("losses")
                .tag("tagname1", "tagvalue1")
                .field("loss", float(self.stat_LOSS))
              )
            self.write_api.write(bucket=self.bucket, org="cilab", record=point_loss)
            
            point_link = (
                Point("links")
                .tag("tagname1", "tagvalue1")
                .field("link", float(self.stat_link))
              )
            self.write_api.write(bucket=self.bucket, org="cilab", record=point_link)
    
            point_obj = (
                Point("objs")
                .tag("tagname1", "tagvalue1")
                .field("obj", float(self.stat_F))
              )
            self.write_api.write(bucket=self.bucket, org="cilab", record=point_obj)

            point_N = (
                Point("Ns")
                .tag("tagname1", "tagvalue1")
                .field("N", float(self.N))
              )
            self.write_api.write(bucket=self.bucket, org="cilab", record=point_N)
            
    def evaluate_objective_function(self, direction):
        obj_function_value=0        
        i = 0
        prev_q = 0
        prev_loss = 0 
        while(i < 10000):
            tmp_stat_LOSS = self.stat_LOSS / 0.05 #0.025#5
            tmp_stat_Q = self.stat_Q
            
            if(direction == 'left'):
                if(tmp_stat_Q < prev_q and tmp_stat_LOSS >= prev_loss):
                    obj_function_value = (self.weight_loss) * tmp_stat_LOSS + (self.weight_delay) * tmp_stat_Q
                    prev_q = tmp_stat_Q
                    prev_loss = tmp_stat_LOSS
                    if(obj_function_value < 1e-4):
                        obj_function_value=0                
                    return obj_function_value
            elif (direction == 'right'):
                #print('right')
                #print('tmp_avg_q: ' + str(tmp_avg_q) +' prev_q: ' + str(prev_q))
                if(tmp_stat_Q > prev_q and tmp_stat_LOSS < prev_loss):
                    obj_function_value = (self.weight_loss) * tmp_stat_LOSS + (self.weight_delay) * tmp_stat_Q
                    prev_q = tmp_stat_Q
                    prev_loss = tmp_stat_LOSS
                    if(obj_function_value < 1e-4):
                        obj_function_value=0                
                    return obj_function_value
            else:
                obj_function_value = (self.weight_loss) * tmp_stat_LOSS + (self.weight_delay) * tmp_stat_Q
                prev_q = tmp_stat_Q
                prev_loss = tmp_stat_LOSS
                if(obj_function_value < 1e-4):
                    obj_function_value=0                
                return obj_function_value
            i+=1
        obj_function_value = (self.weight_loss) * tmp_stat_LOSS + (self.weight_delay) * tmp_stat_Q
        if(prev_q == 0):
            prev_q = tmp_stat_Q
        if(prev_loss == 0):
            prev_loss = tmp_stat_LOSS
        if(obj_function_value < 1e-4):
            obj_function_value=0                
        return obj_function_value
        

    def get_last_obj(self, direction):
        obj_function_values = []
        loss_values = []
        all_obj_func = []
        all_loss = []
        j = 0
        all_obj_func.clear()
        all_loss.clear()
        
        while (j < 10):
            i = 0
            obj_function_values.clear()
            while (i < 10):
                obj_function_value_i = self.evaluate_objective_function(direction)
                loss_values.append(self.stat_LOSS)
                obj_function_values.append(obj_function_value_i)
                i+=1
            obj_func = statistics.mean(obj_function_values)
            loss_result = statistics.mean(loss_values)
            time.sleep(0.05)
            all_obj_func.append(obj_func)
            all_loss.append(loss_result)
            j+=1
        obj_func_final = statistics.mean(all_obj_func)
        loss_final = statistics.mean(all_loss)
        return -obj_func_final,loss_final  
    
    def update_F(self):
        self.avg_F = 0.8 * self.avg_F + 0.2 * self.stat_F
       
    def available_traffic(self):
        return self.N != 0



#measurements = Measurements()

#while(1):
#    print(measurements.get_last_obj('none'))
#    time.sleep(0.1)
