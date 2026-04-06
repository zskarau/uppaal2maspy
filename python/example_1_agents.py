"""
MASPY agents generated from a channel-centric UPPAAL model.
"""
from maspy import *

# ------------------------------------------------------------
# Instance: Prototipo (template: Prototype)
# ------------------------------------------------------------
class Prototipo(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)


    def load_initial_goal(self):
        self.add(Goal("q0"))

    # No channel-centric plans were generated.

if __name__ == "__main__":
    prototipo = Prototipo("Prototipo")
    prototipo.load_initial_goal()
    Admin().start_system()
