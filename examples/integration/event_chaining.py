from pyesys import event
from abc import ABC

class Step(ABC):
    @event
    def on_done(self, data): ...

    @on_done.emitter
    def done(self, data=None): ...


class StepOne(Step):
    def run(self, data=None):
        print("Step 1: Doing work...")
        self.done("data-from-step-1")


class StepTwo(Step):
    def run(self, input_data: str):
        print(f"Step 2: Received '{input_data}', doing more work...")
        self.done("result-from-step-2")


class StepThree(Step):
    def run(self, result: str):
        print(f"Step 3: Finalising with result '{result}'")
        self.done()


s1, s2, s3 = StepOne(), StepTwo(), StepThree()

# Chain events: StepOne → StepTwo → StepThree
s1.on_done += s2.run
s2.on_done += s3.run

# Kick off the chain
s1.run()