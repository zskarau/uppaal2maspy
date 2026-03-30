import xml.etree.ElementTree as ET
import re




# ─── Data Classes ────────────────────────────────────────────────────────────

class NTA:
    def __init__(self):
        self.templates = []       # list of Template
        self.channels = []        # list of Channel (global)
        self.instances = {}       # inst_name -> (tmpl_name, [args])
        self.declarations = None
        self.system = None


class Template:
    def __init__(self, name):
        self.name = name
        self.parameters = []      # list of param names (in declaration order)
        self.clocks = []
        self.locations = []
        self.transitions = []
        self.init = None

    def __str__(self):
        output = []
        output.append(f"\nTemplate: {self.name}")
        output.append(f"Initial state: {self.init}")

        output.append("\nClocks:")
        for clock in self.clocks:
            output.append(f"  {clock.name}: declarado em {self.name}")

        output.append("\nLocations:")
        for loc in self.locations:
            output.append(f"  {loc}")

        output.append("\nTransitions:")
        for trans in self.transitions:
            output.append(f"  {trans}")

        return "\n".join(output)


class Location:
    def __init__(self, id, name=None, invariant=None):
        self.id = id
        self.name = name
        self.invariant = invariant

    def __str__(self):
        return (
            f"Location(id={self.id}, name={self.name}, "
            f"invariant={self.invariant})"
        )


class Clock:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Clock(name={self.name})"


class Channel:
    def __init__(self, name, urgent=False):
        self.name = name
        self.urgent = urgent

    def __str__(self):
        kind = "urgent chan" if self.urgent else "chan"
        return f"Channel(name={self.name}, type={kind})"


class Transition:
    def __init__(self, id, source, target, guard=None, update=None, sync=None):
        self.id = id
        self.source = source
        self.target = target
        self.guard = guard
        self.update = update
        self.sync = sync

    def __str__(self):
        return (
            f"Transition {self.id}(\n"
            f"   from={self.source},\n"
            f"   to={self.target},\n"
            f"   guard={self.guard},\n"
            f"   update={self.update},\n"
            f"   sync={self.sync}\n"
            f")"
        )


# ─── Parsers ─────────────────────────────────────────────────────────────────

def parse_channels_from_system(system_text):
    """Extract global channel declarations from the <s> block."""
    channels = []
    for match in re.finditer(r'(urgent\s+)?chan\s+([\w\s,]+);', system_text):
        urgent = bool(match.group(1))
        for name in match.group(2).split(','):
            name = name.strip()
            if name:
                channels.append(Channel(name, urgent))
    return channels


def parse_instances(system_text):
    """
    Extract instantiations like:
        Door1 = Door(activated1, pushed1, closed1, closed2);
    Returns dict: { 'Door1': ('Door', ['activated1','pushed1','closed1','closed2']) }
    """
    instances = {}
    for match in re.finditer(r'(\w+)\s*=\s*(\w+)\s*\(([^)]*)\)', system_text):
        inst_name = match.group(1)
        tmpl_name = match.group(2)
        args = [a.strip() for a in match.group(3).split(',') if a.strip()]
        instances[inst_name] = (tmpl_name, args)
    return instances


def parse_template_parameters(template_xml):
    """
    Parse template parameter names from:
        <parameter>bool &activated, urgent chan &pushed, ...</parameter>
    Returns list of bare names: ['activated', 'pushed', ...]
    """
    param_text = template_xml.findtext("parameter") or ""
    params = []
    for part in param_text.split(','):
        part = part.strip()
        if part:
            name = re.split(r'[\s&]+', part)[-1]
            params.append(name)
    return params


def parse_template(template_xml):
    name = template_xml.find("name").text
    template = Template(name)

    # parameters
    template.parameters = parse_template_parameters(template_xml)

    # clocks (from local declaration)
    declaration = template_xml.findtext("declaration") or ""
    for match in re.finditer(r'\bclock\s+([\w\s,]+);', declaration):
        for clock_name in match.group(1).split(','):
            clock_name = clock_name.strip()
            if clock_name:
                template.clocks.append(Clock(clock_name))

    # locations (with invariant)
    for loc_xml in template_xml.findall("location"):
        invariant = None
        for label in loc_xml.findall("label"):
            if label.get("kind") == "invariant":
                invariant = label.text
        loc = Location(
            id=loc_xml.get("id"),
            name=loc_xml.findtext("name"),
            invariant=invariant
        )
        template.locations.append(loc)

    # initial state
    init = template_xml.find("init")
    if init is not None:
        template.init = init.get("ref")

    # transitions
    for trans_xml in template_xml.findall("transition"):
        source = trans_xml.find("source").get("ref")
        target = trans_xml.find("target").get("ref")
        tid = trans_xml.get("id")
        guard = update = sync = None

        for label in trans_xml.findall("label"):
            kind = label.get("kind")
            if kind == "guard":
                guard = label.text
            elif kind == "assignment":
                update = label.text
            elif kind == "synchronisation":
                sync = label.text

        template.transitions.append(
            Transition(tid, source, target, guard, update, sync)
        )

    return template


def analyze_communications(nta):
    """
    Resolve sync labels across all instances using parameter mapping.

    For each instance, replace template parameter names in sync labels
    with the actual global channel names from the instantiation call.

    Returns list of tuples:
        (sorted sender list, sorted receiver list, channel_name)
    """
    tmpl_by_name = {t.name: t for t in nta.templates}
    global_chan_names = {c.name for c in nta.channels}

    # inst_channels[inst_name] = (tmpl_name, {param_name: actual_channel})
    inst_channels = {}
    for inst_name, (tmpl_name, args) in nta.instances.items():
        tmpl = tmpl_by_name.get(tmpl_name)
        if not tmpl:
            continue
        mapping = {}
        for param, arg in zip(tmpl.parameters, args):
            if arg in global_chan_names:
                mapping[param] = arg
        inst_channels[inst_name] = (tmpl_name, mapping)

    senders = {}    # channel_actual -> set of instance names
    receivers = {}  # channel_actual -> set of instance names

    for inst_name, (tmpl_name, mapping) in inst_channels.items():
        tmpl = tmpl_by_name.get(tmpl_name)
        if not tmpl:
            continue
        for trans in tmpl.transitions:
            if trans.sync is None:
                continue
            raw = trans.sync.strip()
            if raw.endswith('!'):
                direction, param_name = 'send', raw[:-1]
            elif raw.endswith('?'):
                direction, param_name = 'receive', raw[:-1]
            else:
                continue

            actual = mapping.get(param_name, param_name)

            if direction == 'send':
                senders.setdefault(actual, set()).add(inst_name)
            else:
                receivers.setdefault(actual, set()).add(inst_name)

    comms = []
    for chan in sorted(set(senders) | set(receivers)):
        s_list = sorted(senders.get(chan, {'(unknown)'}))
        r_list = sorted(receivers.get(chan, {'(unknown)'}))
        comms.append((s_list, r_list, chan))
    return comms


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "2doors.xml"
    tree = ET.parse(xml_file)
    root = tree.getroot()

    nta = NTA()

    system_text = ""
    sys_tag = root.find("s") or root.find("system")
    if sys_tag is not None and sys_tag.text:
        system_text = sys_tag.text

    nta.channels = parse_channels_from_system(system_text)
    nta.instances = parse_instances(system_text)

    for template_xml in root.findall("template"):
        template = parse_template(template_xml)
        nta.templates.append(template)

    # ─── Print ────────────────────────────────────────────────────────────────

    for template in nta.templates:
        print(template)

    print("\n" + "="*50)
    print("Global Channels:")
    if nta.channels:
        for ch in nta.channels:
            print(f"  {ch}")
    else:
        print("  (none declared)")

    print("\nCommunications:")
    comms = analyze_communications(nta)
    if comms:
        for s_list, r_list, channel in comms:
            for s in s_list:
                for r in r_list:
                    print(f"  {s} --> {r}  via [{channel}]")
    else:
        print("  (no synchronisations found)")
