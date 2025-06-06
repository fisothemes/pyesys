from pyesys import event

class Engine:

    @event
    def on_start(self): ...

    @event
    def on_stop(self): ...

    @on_start.emitter
    def start(self):
        print("Engine started")

    @on_stop.emitter
    def stop(self):
        print("Engine stopped")

def log_start():
    print("[LOG] Start event received.")

def log_stop():
    print("[LOG] Stop event received.")

engine = Engine()

engine.on_start += log_start
engine.on_stop += log_stop

engine.start()
engine.stop()