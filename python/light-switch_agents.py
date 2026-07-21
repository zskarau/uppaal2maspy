from maspy import *
# ------------------------------------------------------------
# Instance: User1 (template: User)
# ------------------------------------------------------------
class User1(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("idle"))


    @pl(gain, Goal("idle"))
    def idle(self, src, *plan_args):
        self.print(" | ".join(['State: idle (self-loop)', 'sync sending: press']))
        self.send("Light1", achieve, Goal("press"), "press")

# ------------------------------------------------------------
# Instance: Light1 (template: Light)
# ------------------------------------------------------------
class Light1(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("off"))


    @pl(gain, Goal("press"), Goal("on"))
    def on(self, src, *plan_args):
        self.print(" | ".join(['on -> off', 'sync receiving: press']))
        self.add(Goal("off"))

    @pl(gain, Goal("press"), Goal("off"))
    def off(self, src, *plan_args):
        self.print(" | ".join(['off -> on', 'sync receiving: press']))
        self.add(Goal("on"))

if __name__ == "__main__":
    user1 = User1("User1")
    light1 = Light1("Light1")
    press_channel = Channel("press")
    Admin().connect_to([user1, light1], [press_channel])
    Admin().start_system()