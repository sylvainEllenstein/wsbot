#!/usr/bin/env/python3





class MotorThrottle(float):
    pass

class Motor():
    def __init__(self):
        self.throttle = MotorThrottle(0.0)

class MotorKit():
    def __init__(self, inp):
        print(f"Creating Motorkit with some addr = {inp}")
        self.motor1 = Motor()
        self.motor2 = Motor()



