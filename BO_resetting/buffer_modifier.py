import paramiko
import os
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class Buffer_Modifier():
    def __init__(self, hostname, username, password, default_buffer=20000):
        self.buffer = default_buffer
        self.default_buffer = default_buffer
        
        try:
             ## Grafana Plotting below
            token = "INSERT_HERE"
            org = "INSERT_HERE"
            url = "INSERT_HERE"
            client_grafana = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
            self.bucket="p4bs"
            self.write_api = client_grafana.write_api(write_options=SYNCHRONOUS)
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print('*'*60)
            print('Connecting to Legacy Router Management...')
            self.client.connect(hostname=hostname, username=username, password=password)
            self.change_buffer(default_buffer)
            print('Connected!')
            print('*'*60)
            os.system('echo "" > /home/p4bs/configured_buffers')
            os.system('echo '+ str(default_buffer) +' > /home/p4bs/current_buffer')

            print('\n')
                
           
            
        except Exception as e:
            print('Cannot connect to the legacy router')
    
    def change_buffer(self, buffer_size):
        if(buffer_size == self.buffer):
            return -1
        if(buffer_size != 0):
            command = 'edit; set class-of-service schedulers be-scheduler buffer-size temporal ' + str(buffer_size) + ';'
            try:
                stdin, stdout, stderr = self.client.exec_command(command+' commit')
                stdout.read()
                os.system('echo '+ str(buffer_size) +' > /home/p4bs/current_buffer')
                self.buffer = buffer_size
                point_buffer_size = (
                    Point("buffers")
                    .tag("tagname1", "tagvalue1")
                    .field("buffer", float(float(buffer_size) / 200000.0))
                  )
                self.write_api.write(bucket=self.bucket, org="cilab", record=point_buffer_size)
            except Exception as e:
                print('Cannot change buffer size')
            return 0
        return -1
        
