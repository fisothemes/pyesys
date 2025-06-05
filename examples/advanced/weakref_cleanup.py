import gc
from pyesys import create_event
 
event, listener = create_event(example=lambda x: None)
 
class Greeter:
    def hello(self, name):
        print(f"Hello, {name}!")
 
g = Greeter()
listener += g.hello
assert event.handler_count() == 1
 
# Remove the only reference
del g
gc.collect()
 
# Handler should be cleaned up
assert event.handler_count() == 0
print("Handler cleaned up after GC.")