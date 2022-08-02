from Comms import bootbt
from Comms.btcon import BTCon
from IMU.abstract_adcs import ADCS
import sys
import subprocess
import time
import threading
import numpy as np

from picamera import PiCamera #delete this

class Cubesat:
    def __init__(self, otherpi):
        self.otherpi = otherpi
        self.adcs = ADCS()
        self.state = "commission"
        self.orbit = 0
        self.orbit_floor = -0.5
        self.image_queue = []
        self.image_comms = False
        self.cur_image = 1#TODO change this
        
        self.camera = PiCamera()

    def main(self, otherpi):
        while self.orbit < 10 and self.state != "sleep":
            if self.state == "nominal":
                self.nominal() 
            elif self.state == "science":
                self.science()
            elif self.state == "comms":
                self.comms()         
            elif self.state == "commission":
                self.commission()
            elif self.state == "error":
                self.error()
            elif self.state == "safe":
                self.safe()
        self.sleep()

    def nominal(self):
        while self.state == "nominal": 
            print("nominal")
            time.sleep(1)
            self.orbit = (time.time() - self.start_time) / 8
            if self.orbit - self.orbit_floor > 1:
                self.state = "comms" 
            if orbit > 1 and orbit < 3 and np.mod(orbit, 0.55) < 0.125:
                self.state = "science" 
            elif orbit > 8:
                self.state = "comms"
                self.image_comms = True
            #TODO: add checks for angle, etc to switch state 
            self.orbit_floor = np.floor(self.orbit) - 0.5 #TODO change this to adapt to HABs being at comm time
    
    def science(self): #TODO
        print("science")
        name = f"image_{self.cur_image}"
        hab = 1 #find this from processing
        #take image, process it, add adcs data to it
        camera.capture("/home/pi/CHARMS/Images/{name}.jpg")
        t = time.localtime()
        data = (f"{name}\n{time.strftime('%H:%M:%S', t)}\n"
        f"angle: {self.adcs.get_yaw()}\nhab angle:{hab}")
        with open("/home/pi/CHARMS/Images/{name}.txt", "w") as f:
            f.write(data)
        #add to self.image_queue depending on quality of image
        self.image_queue.append(name)
    
    def comms(self): 
        print("comms")
        self.connection.connect_repeat_again_as_client(1, 3)
        self.send_telemetry() 
        if self.image_comms:
            self.connection.write_raw("image_first")
            self.connection.connect_as_host(2)
            for img in self.image_queue:
                self.connection.write_raw("again")
                self.send_image(img)            
        self.connection.write_raw("done")        
        self.connection.close_all_connections()

    def commission(self):
        print("commission")
        self.adcs.calibrate()
        self.adcs.initial_angle()
        print("running connection test")
        self.connection=bootbt.bt_selftest(self.otherpi, "True")
        print("connected and waiting for ready")
        self.connection.receive_raw()
        print("ready received")
        self.connection.close_all_connections()
        self.start_time = time.time()
        self.adcs_thread = threading.Thread(target=self.run_adcs, daemon=True)
        self.adcs_thread.start()
        self.state = "nominal"
        
        
    def error(self): #TODO
        print("error")

    def sleep(self):
        print("sleep")
        self.connection.connect_repeat_again_as_client(1, 3)
        self.connection.write_raw("sleep")
        self.connection.write_raw("done")
        self.connection.close_all_connections()
        #TODO: shutdown somehow: subprocess?
    
    def safe(self):#TODO
        print("safe")
    
    def send_telemetry(self): #Connect as client before calling
        self.connection.write_raw("telemetry")
        t = time.localtime()
        send_data = (f"{time.strftime('%H:%M:%S', t)}\norbit: {self.orbit}\nangle: {self.adcs.get_yaw()}\n"
        f"{subprocess.check_output(['vcgencmd', 'measure_temp']).decode('UTF-8')}")
        self.connection.write_string(send_data)

    def send_image(self, name): #connect as client and host before calling
        start_time = time.time()
        self.connection.write_raw("image")
        self.connection.write_raw(name)
        while True:
            self.connection.write_image(f"/home/pi/CHARMS/Images/{name}.jpg")
            reply = self.connection.receive_raw() #DO NOT TRY TO CONNECT AGAIN WHILE THE GROUND STATION IS RECEIVING DATA
            if reply == "done":
                break #otherwise error received
        with open("/home/pi/CHARMS/Images/{name}.txt", "r") as f:
            self.connection.write_string(f.read())
        print(time.time() - start_time)

    def run_adcs(self):
        while True:
            time.sleep(0.5)
            self.adcs.update_yaw_average()
            print("adcs")
        
if __name__ == "__main__":
    otherpi = sys.argv[1]#name of other pi hostname
    realRun = sys.argv[2]#whether this is the 1st/2nd time run in startup.sh
    cubesat = Cubesat(otherpi)
    if realRun == "True":
        cubesat.main(otherpi)
    else:
        bootbt.bt_selftest(otherpi, "True")        
