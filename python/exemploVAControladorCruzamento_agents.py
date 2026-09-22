import random
from maspy import *
# ------------------------------------------------------------
# Instance: carro1 (template: VA)
# ------------------------------------------------------------
class carro1(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)


    def _set_belief(self, name, value):
        for belief in list(self.belief_list):
            if belief.name == name and belief.source == "self":
                self.rm(belief)
        self.add(Belief(name, value))

    def load_initial_goal(self):
        self.add(Goal("Longe"))

    @pl(gain, Goal("Ocupado"))
    # temporal guard ignored: aguardar > 3
    def Ocupado_1(self, src, *plan_args):
        self.print(" | ".join(['Ocupado -> NoCruzamento']))
        # temporal update ignored: aguardar = 0
        self.add(Goal("NoCruzamento"))

    @pl(gain, Goal("Cruzando"))
    def Cruzando(self, src, *plan_args):
        self.print(" | ".join(['Cruzando -> Longe', 'sync sending: longe']))
        self.send("cont1", achieve, Goal("longe"), "longe")
        self.add(Goal("Longe"))

    @pl(gain, Goal("Livre"))
    def Livre(self, src, *plan_args):
        self.print(" | ".join(['Livre -> Cruzando']))
        self.add(Goal("Cruzando"))

    @pl(gain, Goal("ocupado"), Goal("NoCruzamento"))
    def NoCruzamento_1(self, src, *plan_args):
        self.print(" | ".join(['NoCruzamento -> Ocupado', 'sync receiving: ocupado']))
        self.add(Goal("Ocupado"))

    @pl(gain, Goal("livre"), Goal("NoCruzamento"))
    def NoCruzamento_2(self, src, *plan_args):
        self.print(" | ".join(['NoCruzamento -> Livre', 'sync receiving: livre']))
        self.add(Goal("Livre"))

    @pl(gain, Goal("Longe"))
    def Longe(self, src, *plan_args):
        self.print(" | ".join(['Longe -> NoCruzamento', 'sync sending: proximo']))
        self.send("cont1", achieve, Goal("proximo"), "proximo")
        self.add(Goal("NoCruzamento"))

# ------------------------------------------------------------
# Instance: cont1 (template: Controlador)
# ------------------------------------------------------------
class cont1(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)


    def _set_belief(self, name, value):
        for belief in list(self.belief_list):
            if belief.name == name and belief.source == "self":
                self.rm(belief)
        self.add(Belief(name, value))

    def load_initial_goal(self):
        self.add(Goal("Idle"))

    @pl(gain, Goal("longe"), Goal("Livre"))
    def Livre_1(self, src, *plan_args):
        self.print(" | ".join(['Livre -> Idle', 'sync receiving: longe']))
        self.add(Goal("Idle"))

    @pl(gain, Goal("Livre"))
    def Livre_2(self, src, *plan_args):
        self.print(" | ".join(['Livre -> Ocupado', 'sync sending: ocupado']))
        self.send("carro1", achieve, Goal("ocupado"), "ocupado")
        self.add(Goal("Ocupado"))

    @pl(gain, Goal("Ocupado"))
    def Ocupado(self, src, *plan_args):
        self.print(" | ".join(['Ocupado -> Livre', 'sync sending: livre']))
        self.send("carro1", achieve, Goal("livre"), "livre")
        self.add(Goal("Livre"))

    @pl(gain, Goal("proximo"), Goal("Idle"))
    def Idle(self, src, *plan_args):
        self.print(" | ".join(['Idle -> Livre', 'sync receiving: proximo']))
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
