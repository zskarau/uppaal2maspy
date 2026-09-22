import random
from maspy import *
# ------------------------------------------------------------
# Instance: carro1 (template: VA)
# ------------------------------------------------------------
class carro1(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)

        self.add(Belief("noCruzamento", "false", adds_event=False))
        self.add(Belief("livre", 0, adds_event=False))

    def _set_belief(self, name, value):
        for belief in list(self.belief_list):
            if belief.name == name and belief.source == "self":
                self.rm(belief)
        self.add(Belief(name, value, adds_event=False))

    def _receiver_ready(self, target, expected_states):
        state = self.send(target, askOneReply, Belief("__state", Any))
        return bool(state and state.values in expected_states)

    def load_initial_goal(self):
        self._set_belief("__state", "Longe")
        self.add(Goal("Longe"))

    @pl(gain, Goal("Ocupado"), Belief("__state", "Ocupado"))
    # temporal guard ignored: aguardar > 3
    def Ocupado_1(self, src, *plan_args):
        self.print(" | ".join(['Ocupado -> NoCruzamento']))
        rand = random.randint(0, 1)
        self._set_belief("livre", rand)
        # temporal update ignored: aguardar = 0
        self._set_belief("__state", "NoCruzamento")
        self.add(Goal("NoCruzamento"))

    @pl(gain, Goal("Cruzando"), [Belief("__state", "Cruzando"), Belief("noCruzamento", "true")])
    def Cruzando(self, src, *plan_args):
        self.print(" | ".join(['Cruzando -> Longe']))
        self._set_belief("noCruzamento", "false")
        self._set_belief("__state", "Longe")
        self.add(Goal("Longe"))

    @pl(gain, Goal("Livre"), Belief("__state", "Livre"))
    def Livre(self, src, *plan_args):
        self.print(" | ".join(['Livre -> Cruzando']))
        self._set_belief("__state", "Cruzando")
        self.add(Goal("Cruzando"))

    @pl(gain, Goal("NoCruzamento"), [Belief("__state", "NoCruzamento"), Belief("livre", 0)])
    def NoCruzamento_1(self, src, *plan_args):
        self.print(" | ".join(['NoCruzamento -> Ocupado']))
        self._set_belief("__state", "Ocupado")
        self.add(Goal("Ocupado"))

    @pl(gain, Goal("NoCruzamento"), [Belief("__state", "NoCruzamento"), Belief("livre", 1)])
    def NoCruzamento_2(self, src, *plan_args):
        self.print(" | ".join(['NoCruzamento -> Livre']))
        self._set_belief("__state", "Livre")
        self.add(Goal("Livre"))

    @pl(gain, Goal("Longe"), Belief("__state", "Longe"))
    def Longe(self, src, *plan_args):
        self.print(" | ".join(['Longe -> NoCruzamento']))
        rand = random.randint(0, 1)
        self._set_belief("noCruzamento", "true")
        self._set_belief("livre", rand)
        self._set_belief("__state", "NoCruzamento")
        self.add(Goal("NoCruzamento"))

if __name__ == "__main__":
    carro1 = carro1("carro1")
    carro1.load_initial_goal()
    Admin().start_system()
