import random
from maspy import *
# ------------------------------------------------------------
# Instance: User1 (template: User)
# ------------------------------------------------------------
class User1(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)


    def _set_belief(self, name, value):
        for belief in list(self.belief_list):
            if belief.name == name and belief.source == "self":
                self.rm(belief)
        self.add(Belief(name, value, adds_event=False))

    def _receiver_ready(self, target, expected_states):
        state = self.send(target, askOneReply, Belief("__state", Any))
        return bool(state and state.values in expected_states)

    def load_initial_goal(self):
        self._set_belief("__state", "idle")
        self.add(Goal("idle"))

    @pl(gain, Goal("idle"), Belief("__state", "idle"))
    def idle(self, src, *plan_args):
        self.print(" | ".join(['State: idle (self-loop)', 'sync sending: press']))
        sent_sync = False
        if self._receiver_ready("Light1", ['off', 'on']):
            self.send("Light1", achieve, Goal("press"), "press")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("idle"))
            return
        self.add(Goal("idle"))

# ------------------------------------------------------------
# Instance: Light1 (template: Light)
# ------------------------------------------------------------
class Light1(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)


    def _set_belief(self, name, value):
        for belief in list(self.belief_list):
            if belief.name == name and belief.source == "self":
                self.rm(belief)
        self.add(Belief(name, value, adds_event=False))

    def _receiver_ready(self, target, expected_states):
        state = self.send(target, askOneReply, Belief("__state", Any))
        return bool(state and state.values in expected_states)

    def load_initial_goal(self):
        self._set_belief("__state", "off")

    @pl(gain, Goal("press"), Belief("__state", "on"))
    def on(self, src, *plan_args):
        self.print(" | ".join(['on -> off', 'sync receiving: press']))
        self._set_belief("__state", "off")

    @pl(gain, Goal("press"), Belief("__state", "off"))
    def off(self, src, *plan_args):
        self.print(" | ".join(['off -> on', 'sync receiving: press']))
        self._set_belief("__state", "on")

if __name__ == "__main__":
    user1 = User1("User1")
    light1 = Light1("Light1")
    press_channel = Channel("press")
    Admin().connect_to([user1, light1], [press_channel])
    user1.load_initial_goal()
    light1.load_initial_goal()
    Admin().start_system()
