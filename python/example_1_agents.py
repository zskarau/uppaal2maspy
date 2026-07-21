from maspy import *
# ------------------------------------------------------------
# Instance: Prototipo (template: Prototype)
# ------------------------------------------------------------
class Prototipo(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)


    def load_initial_goal(self):
        self.add(Goal("q0"))

    @pl(gain, Goal("q0"))
    # temporal guard ignored: x>=0
    def q0_1(self, src, *plan_args):
        self.print(" | ".join(['q0 -> q1']))
        self.add(Goal("q1"))

if __name__ == "__main__":
    prototipo = Prototipo("Prototipo")
    prototipo.load_initial_goal()
    Admin().start_system()
