import random
from maspy import *
MAX_AGENT_TRANSITIONS = 50
# ------------------------------------------------------------
# Instance: carro1 (template: VA)
# ------------------------------------------------------------
class carro1(Agent):
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
        self._set_belief("__state", "Longe")
        self.add(Goal("Longe"))

    @pl(gain, Goal("Ocupado"), Belief("__state", "Ocupado"))
    # temporal guard ignored: aguardar > 3
    def Ocupado_1(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Ocupado -> NoCruzamento']))
        # temporal update ignored: aguardar = 0
        self._set_belief("__state", "NoCruzamento")

    @pl(gain, Goal("Cruzando"), Belief("__state", "Cruzando"))
    def Cruzando(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Cruzando -> Longe', 'sync sending: longe']))
        self.send("cont1", achieve, Goal("longe"), "longe")
        self._set_belief("__state", "Longe")
        self.add(Goal("Longe"))

    @pl(gain, Goal("Livre"), Belief("__state", "Livre"))
    def Livre(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Livre -> Cruzando']))
        self._set_belief("__state", "Cruzando")
        self.add(Goal("Cruzando"))

    @pl(gain, Goal("ocupado"), Belief("__state", "NoCruzamento"))
    def NoCruzamento_1(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['NoCruzamento -> Ocupado', 'sync receiving: ocupado']))
        self._set_belief("__state", "Ocupado")
        self.add(Goal("Ocupado"))

    @pl(gain, Goal("livre"), Belief("__state", "NoCruzamento"))
    def NoCruzamento_2(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['NoCruzamento -> Livre', 'sync receiving: livre']))
        self._set_belief("__state", "Livre")
        self.add(Goal("Livre"))

    @pl(gain, Goal("Longe"), Belief("__state", "Longe"))
    def Longe(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Longe -> NoCruzamento', 'sync sending: proximo']))
        self.send("cont1", achieve, Goal("proximo"), "proximo")
        self._set_belief("__state", "NoCruzamento")

# ------------------------------------------------------------
# Instance: cont1 (template: Controlador)
# ------------------------------------------------------------
class cont1(Agent):
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
        self._set_belief("__state", "Idle")

    @pl(gain, Goal("longe"), Belief("__state", "Livre"))
    def Livre_1(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Livre -> Idle', 'sync receiving: longe']))
        self._set_belief("__state", "Idle")

    @pl(gain, Goal("Livre"), Belief("__state", "Livre"))
    def Livre_2(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Livre -> Ocupado', 'sync sending: ocupado']))
        self.send("carro1", achieve, Goal("ocupado"), "ocupado")
        self._set_belief("__state", "Ocupado")
        self.add(Goal("Ocupado"))

    @pl(gain, Goal("Ocupado"), Belief("__state", "Ocupado"))
    def Ocupado(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Ocupado -> Livre', 'sync sending: livre']))
        self.send("carro1", achieve, Goal("livre"), "livre")
        self._set_belief("__state", "Livre")
        self.add(Goal("Livre"))

    @pl(gain, Goal("proximo"), Belief("__state", "Idle"))
    def Idle(self, src, *plan_args):
        if not self._begin_transition():
            return
        self.print(" | ".join(['Idle -> Livre', 'sync receiving: proximo']))
        self._set_belief("__state", "Livre")
        self.add(Goal("Livre"))

if __name__ == "__main__":
    carro1 = carro1("carro1")
    cont1 = cont1("cont1")
    livre_channel = Channel("livre")
    longe_channel = Channel("longe")
    proximo_channel = Channel("proximo")
    ocupado_channel = Channel("ocupado")
    Admin().connect_to([carro1, cont1], [livre_channel, longe_channel, proximo_channel, ocupado_channel])
    carro1.load_initial_goal()
    cont1.load_initial_goal()
    Admin().start_system()
