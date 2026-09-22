import random
from maspy import *
# ------------------------------------------------------------
# Instance: Door1 (template: Door)
# ------------------------------------------------------------
class Door1(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)

        self.add(Belief("activated", "false", adds_event=False))

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

    @pl(gain, Goal("closed"), Belief("__state", "closed"))
    def closed_1(self, src, *plan_args):
        self.print(" | ".join(['State: closed (self-loop)', 'sync sending: closed1']))
        sent_sync = False
        if self._receiver_ready("Door2", ['wait']):
            self.send("Door2", achieve, Goal("closed1"), "closed1")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("closed"))
            return
        self.add(Goal("closed"))

    @pl(gain, Goal("closed"), Belief("__state", "closed"))
    # temporal guard ignored: x>=5
    def closed_2(self, src, *plan_args):
        self.print(" | ".join(['closed -> idle']))
        self._set_belief("__state", "idle")
        self.add(Goal("idle"))

    @pl(gain, Goal("closing"), Belief("__state", "closing"))
    # temporal guard ignored: x==6
    def closing(self, src, *plan_args):
        self.print(" | ".join(['closing -> closed']))
        self._set_belief("activated", "false")
        # temporal update ignored: x=0
        self._set_belief("__state", "closed")
        self.add(Goal("closed"))

    @pl(gain, Goal("idle"), Belief("__state", "idle"))
    def idle_1(self, src, *plan_args):
        self.print(" | ".join(['State: idle (self-loop)', 'sync sending: closed1']))
        sent_sync = False
        if self._receiver_ready("Door2", ['wait']):
            self.send("Door2", achieve, Goal("closed1"), "closed1")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("idle"))
            return
        self.add(Goal("idle"))

    @pl(gain, Goal("pushed1"), Belief("__state", "idle"))
    def idle_2(self, src, *plan_args):
        self.print(" | ".join(['idle -> wait', 'sync receiving: pushed1']))
        self._set_belief("activated", "true")
        self._set_belief("__state", "wait")
        self.add(Goal("wait"))

    @pl(gain, Goal("open"), Belief("__state", "open"))
    # temporal guard ignored: x>=4
    def open(self, src, *plan_args):
        self.print(" | ".join(['open -> closing']))
        # temporal update ignored: x=0
        self._set_belief("__state", "closing")
        self.add(Goal("closing"))

    @pl(gain, Goal("opening"), Belief("__state", "opening"))
    # temporal guard ignored: x==6
    def opening(self, src, *plan_args):
        self.print(" | ".join(['opening -> open']))
        # temporal update ignored: x=0
        self._set_belief("__state", "open")
        self.add(Goal("open"))

    @pl(gain, Goal("closed2"), Belief("__state", "wait"))
    def wait_1(self, src, *plan_args):
        self.print(" | ".join(['wait -> opening', 'sync receiving: closed2']))
        # temporal update ignored: x=0
        self._set_belief("__state", "opening")
        self.add(Goal("opening"))

    @pl(gain, Goal("wait"), Belief("__state", "wait"))
    def wait_2(self, src, *plan_args):
        self.print(" | ".join(['State: wait (self-loop)', 'sync sending: closed1']))
        sent_sync = False
        if self._receiver_ready("Door2", ['wait']):
            self.send("Door2", achieve, Goal("closed1"), "closed1")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("wait"))
            return
        self.add(Goal("wait"))

# ------------------------------------------------------------
# Instance: Door2 (template: Door)
# ------------------------------------------------------------
class Door2(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)

        self.add(Belief("activated", "false", adds_event=False))

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

    @pl(gain, Goal("closed"), Belief("__state", "closed"))
    def closed_1(self, src, *plan_args):
        self.print(" | ".join(['State: closed (self-loop)', 'sync sending: closed2']))
        sent_sync = False
        if self._receiver_ready("Door1", ['wait']):
            self.send("Door1", achieve, Goal("closed2"), "closed2")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("closed"))
            return
        self.add(Goal("closed"))

    @pl(gain, Goal("closed"), Belief("__state", "closed"))
    # temporal guard ignored: x>=5
    def closed_2(self, src, *plan_args):
        self.print(" | ".join(['closed -> idle']))
        self._set_belief("__state", "idle")
        self.add(Goal("idle"))

    @pl(gain, Goal("closing"), Belief("__state", "closing"))
    # temporal guard ignored: x==6
    def closing(self, src, *plan_args):
        self.print(" | ".join(['closing -> closed']))
        self._set_belief("activated", "false")
        # temporal update ignored: x=0
        self._set_belief("__state", "closed")
        self.add(Goal("closed"))

    @pl(gain, Goal("idle"), Belief("__state", "idle"))
    def idle_1(self, src, *plan_args):
        self.print(" | ".join(['State: idle (self-loop)', 'sync sending: closed2']))
        sent_sync = False
        if self._receiver_ready("Door1", ['wait']):
            self.send("Door1", achieve, Goal("closed2"), "closed2")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("idle"))
            return
        self.add(Goal("idle"))

    @pl(gain, Goal("pushed2"), Belief("__state", "idle"))
    def idle_2(self, src, *plan_args):
        self.print(" | ".join(['idle -> wait', 'sync receiving: pushed2']))
        self._set_belief("activated", "true")
        self._set_belief("__state", "wait")
        self.add(Goal("wait"))

    @pl(gain, Goal("open"), Belief("__state", "open"))
    # temporal guard ignored: x>=4
    def open(self, src, *plan_args):
        self.print(" | ".join(['open -> closing']))
        # temporal update ignored: x=0
        self._set_belief("__state", "closing")
        self.add(Goal("closing"))

    @pl(gain, Goal("opening"), Belief("__state", "opening"))
    # temporal guard ignored: x==6
    def opening(self, src, *plan_args):
        self.print(" | ".join(['opening -> open']))
        # temporal update ignored: x=0
        self._set_belief("__state", "open")
        self.add(Goal("open"))

    @pl(gain, Goal("closed1"), Belief("__state", "wait"))
    def wait_1(self, src, *plan_args):
        self.print(" | ".join(['wait -> opening', 'sync receiving: closed1']))
        # temporal update ignored: x=0
        self._set_belief("__state", "opening")
        self.add(Goal("opening"))

    @pl(gain, Goal("wait"), Belief("__state", "wait"))
    def wait_2(self, src, *plan_args):
        self.print(" | ".join(['State: wait (self-loop)', 'sync sending: closed2']))
        sent_sync = False
        if self._receiver_ready("Door1", ['wait']):
            self.send("Door1", achieve, Goal("closed2"), "closed2")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("wait"))
            return
        self.add(Goal("wait"))

# ------------------------------------------------------------
# Instance: User1 (template: User)
# ------------------------------------------------------------
class User1(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)

        self.add(Belief("activated", "false", adds_event=False))

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

    @pl(gain, Goal("idle"), [Belief("__state", "idle"), Belief("activated", "false")])
    def idle(self, src, *plan_args):
        self.print(" | ".join(['idle -> id15']))
        # temporal update ignored: w=0
        self._set_belief("__state", "id15")
        self.add(Goal("id15"))

    @pl(gain, Goal("id15"), Belief("__state", "id15"))
    def id15(self, src, *plan_args):
        self.print(" | ".join(['id15 -> idle', 'sync sending: pushed1']))
        sent_sync = False
        if self._receiver_ready("Door1", ['idle']):
            self.send("Door1", achieve, Goal("pushed1"), "pushed1")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("id15"))
            return
        self._set_belief("__state", "idle")
        self.add(Goal("idle"))

# ------------------------------------------------------------
# Instance: User2 (template: User)
# ------------------------------------------------------------
class User2(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)

        self.add(Belief("activated", "false", adds_event=False))

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

    @pl(gain, Goal("idle"), [Belief("__state", "idle"), Belief("activated", "false")])
    def idle(self, src, *plan_args):
        self.print(" | ".join(['idle -> id15']))
        # temporal update ignored: w=0
        self._set_belief("__state", "id15")
        self.add(Goal("id15"))

    @pl(gain, Goal("id15"), Belief("__state", "id15"))
    def id15(self, src, *plan_args):
        self.print(" | ".join(['id15 -> idle', 'sync sending: pushed2']))
        sent_sync = False
        if self._receiver_ready("Door2", ['idle']):
            self.send("Door2", achieve, Goal("pushed2"), "pushed2")
            sent_sync = True
        if not sent_sync:
            self.add(Goal("id15"))
            return
        self._set_belief("__state", "idle")
        self.add(Goal("idle"))

if __name__ == "__main__":
    door1 = Door1("Door1")
    door2 = Door2("Door2")
    user1 = User1("User1")
    user2 = User2("User2")
    pushed1_channel = Channel("pushed1")
    pushed2_channel = Channel("pushed2")
    closed1_channel = Channel("closed1")
    closed2_channel = Channel("closed2")
    Admin().connect_to([door1, door2, user1, user2], [pushed1_channel, pushed2_channel, closed1_channel, closed2_channel])
    door1.load_initial_goal()
    door2.load_initial_goal()
    user1.load_initial_goal()
    user2.load_initial_goal()
    Admin().start_system()
