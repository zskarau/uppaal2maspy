import random
from maspy import *
# ------------------------------------------------------------
# Instance: Prototipo (template: Prototype)
# ------------------------------------------------------------
class Prototipo(Agent):
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
        self._set_belief("__state", "q0")
        self.add(Goal("q0"))

    @pl(gain, Goal("q0"), Belief("__state", "q0"))
    # temporal guard ignored: x>=0
    def q0_1(self, src, *plan_args):
        self.print(" | ".join(['q0 -> q1']))
        self._set_belief("__state", "q1")

if __name__ == "__main__":
    prototipo = Prototipo("Prototipo")
    prototipo.load_initial_goal()
    Admin().start_system()
