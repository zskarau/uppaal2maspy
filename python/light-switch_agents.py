from maspy import *

class User(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("idle"))

    @pl(gain, Goal("idle"))
    def idle(self, src, *plan_args):
        self.print(" | ".join(['State: idle (self-loop)', 'sync sending: press']))
        self.send("Light", achieve, Goal("press"), "press")
        self.add(Goal("idle"))

class Light(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Belief("off"))

    @pl(gain, Goal("press"), Belief("on"))
    def on(self, src, *plan_args):
        self.print(" | ".join(['on -> off', 'sync receiving: press']))
        self.rm(Belief("on"))
        self.add(Belief("off"))

    @pl(gain, Goal("press"), Belief("off"))
    def off(self, src, *plan_args):
        self.print(" | ".join(['off -> on', 'sync receiving: press']))
        self.rm(Belief("off"))
        self.add(Belief("on"))

if __name__ == "__main__":
    user = User("User")
    light = Light("Light")
    press_channel = Channel("press")
    Admin().connect_to([user, light], [press_channel])
    Admin().start_system()
