import random
from maspy import *
MAX_AGENT_TRANSITIONS = 50
# ------------------------------------------------------------
# Instance: Prototipo (template: Prototype)
# ------------------------------------------------------------
class Prototipo(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self._transition_count = 0


    def _set_belief(self, name, value):
        for belief in list(self.belief_list):
            if belief.name == name and belief.source == "self":
                self.rm(belief)
        self.add(Belief(name, value, adds_event=False))

    def _begin_transition(self):
        if self._transition_count >= MAX_AGENT_TRANSITIONS:
            self.print("Maximum transition limit reached")
            Admin().stop_system()
            return False
        self._transition_count += 1
        return True

    def load_initial_goal(self):
        self._set_belief("__state", "q0")
        self.add(Goal("q0"))

    @pl(gain, Goal("q0"), Belief("__state", "q0"))
    # temporal guard ignored: x>=0
    def q0_1(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['q0 -> q1']))
        self._set_belief("__state", "q1")
        self.stop_cycle()

if __name__ == "__main__":
    prototipo = Prototipo("Prototipo")
    prototipo.load_initial_goal()
    Admin().start_system()
