import re
import xml.etree.ElementTree as ET


CHANNEL_DECLARATION_RE = re.compile(
    r"(?P<urgent>urgent\s+)?chan\s+(?P<names>[^;]+);"
)
INSTANCE_RE = re.compile(
    r"(?P<instance>\w+)\s*=\s*(?P<template>\w+)\s*\((?P<args>[^)]*)\)"
)


class NTA:
    def __init__(self):
        self.templates = []
        self.channels = []
        self.instances = {}
        self.declarations = None
        self.system = None


class Template:
    def __init__(self, name):
        self.name = name
        self.parameters = []
        self.parameter_kinds = {}
        self.variables = {}
        self.temporal_vars = set()
        self.locations = []
        self.transitions = []
        self.init = None

    def __str__(self):
        output = []
        output.append(f"\nTemplate: {self.name}")
        output.append(f"Initial state: {self.init}")

        if self.parameters:
            output.append("\nParameters:")
            for param in self.parameters:
                kind = self.parameter_kinds.get(param, "value")
                output.append(f"  {param} ({kind})")

        if self.variables:
            output.append("\nVariables:")
            for var_name, var_info in self.variables.items():
                output.append(
                    f"  {var_name} ({var_info['kind']}, initial={var_info['initial']})"
                )

        output.append("\nLocations:")
        for loc in self.locations:
            output.append(f"  {loc}")

        output.append("\nTransitions:")
        for trans in self.transitions:
            output.append(f"  {trans}")

        return "\n".join(output)


class Location:
    def __init__(self, id, name=None):
        self.id = id
        self.name = name

    def __str__(self):
        return f"Location(id={self.id}, name={self.name})"


class Channel:
    def __init__(self, name, urgent=False):
        self.name = name
        self.urgent = urgent

    def __str__(self):
        kind = "urgent chan" if self.urgent else "chan"
        return f"Channel(name={self.name}, type={kind})"


class Transition:
    def __init__(
        self, id, source, target, guard=None, update=None, sync=None, select=None
    ):
        self.id = id
        self.source = source
        self.target = target
        self.guard = guard
        self.update = update
        self.sync = sync
        self.select = select

    def __str__(self):
        return (
            f"Transition {self.id}(\n"
            f"   from={self.source},\n"
            f"   to={self.target},\n"
            f"   guard={self.guard},\n"
            f"   update={self.update},\n"
            f"   sync={self.sync},\n"
            f"   select={self.select}\n"
            f")"
        )


def get_system_text(root):
    sys_tag = root.find("s") or root.find("system")
    return sys_tag.text if sys_tag is not None and sys_tag.text else ""


def normalize_channel_name(raw):
    if raw is None:
        return None

    normalized = raw.strip().rstrip("!?").strip()
    normalized = re.sub(r"\[.*\]$", "", normalized)
    return normalized.strip() or None


def resolve_sync_label(sync_label, param_map=None):
    if not sync_label:
        return None, None, None

    raw = sync_label.strip()
    if raw.endswith("!"):
        direction = "send"
        label = raw[:-1]
    elif raw.endswith("?"):
        direction = "receive"
        label = raw[:-1]
    else:
        return None, None, None

    mapping = param_map or {}
    actual = mapping.get(label, label)
    return direction, normalize_channel_name(actual), actual


def parse_channels_from_text(text):
    channels = {}
    if not text:
        return []

    for match in CHANNEL_DECLARATION_RE.finditer(text):
        urgent = bool(match.group("urgent"))
        for declared_name in match.group("names").split(","):
            name = normalize_channel_name(declared_name)
            if name and name not in channels:
                channels[name] = Channel(name, urgent)

    return list(channels.values())


def parse_channels(root):
    channels = {}
    for text in (root.findtext("declaration") or "", get_system_text(root)):
        for channel in parse_channels_from_text(text):
            channels.setdefault(channel.name, channel)
    return list(channels.values())


def parse_channels_from_system(system_text):
    return parse_channels_from_text(system_text)


def parse_instances(system_text):
    """
    Extract instantiations like:
        Door1 = Door(activated1, pushed1, closed1, closed2);
    Returns dict:
        {'Door1': ('Door', ['activated1', 'pushed1', 'closed1', 'closed2'])}
    """

    instances = {}
    for match in INSTANCE_RE.finditer(system_text):
        inst_name = match.group("instance")
        tmpl_name = match.group("template")
        args = [arg.strip() for arg in match.group("args").split(",") if arg.strip()]
        instances[inst_name] = (tmpl_name, args)
    return instances


def parse_template_parameters(template_xml):
    """
    Parse template parameters and classify the kind of each parameter.

    Example:
        <parameter>bool &activated, urgent chan &pushed</parameter>
    """

    param_text = template_xml.findtext("parameter") or ""
    params = []
    kinds = {}

    for part in param_text.split(","):
        raw_part = part.strip()
        if not raw_part:
            continue

        name = re.split(r"[\s&]+", raw_part)[-1]
        if "chan" in raw_part:
            kind = "channel"
        elif re.search(r"\bbool\b", raw_part):
            kind = "bool"
        else:
            kind = "value"

        params.append(name)
        kinds[name] = kind

    return params, kinds


def parse_template_variables(declaration):
    variables = {}
    if not declaration:
        return variables

    clean_lines = []
    for line in declaration.splitlines():
        clean_lines.append(line.split("//", 1)[0])
    clean_declaration = "\n".join(clean_lines)

    for match in re.finditer(
        r"\b(?P<kind>bool|int)\s+(?P<name>\w+)"
        r"(?:\s*=\s*(?P<initial>[^;]+))?\s*;",
        clean_declaration,
    ):
        kind = match.group("kind")
        initial = match.group("initial")
        if initial is None:
            initial = "false" if kind == "bool" else "0"

        variables[match.group("name")] = {
            "kind": kind,
            "initial": initial.strip(),
        }

    return variables


def parse_template(template_xml):
    name = template_xml.find("name").text
    template = Template(name)

    template.parameters, template.parameter_kinds = parse_template_parameters(
        template_xml
    )

    declaration = template_xml.findtext("declaration") or ""
    template.variables = parse_template_variables(declaration)
    for match in re.finditer(r"\bclock\s+([\w\s,]+);", declaration):
        for clock_name in match.group(1).split(","):
            clock_name = clock_name.strip()
            if clock_name:
                template.temporal_vars.add(clock_name)

    for loc_xml in template_xml.findall("location"):
        template.locations.append(
            Location(
                id=loc_xml.get("id"),
                name=loc_xml.findtext("name"),
            )
        )

    init = template_xml.find("init")
    if init is not None:
        template.init = init.get("ref")

    for trans_xml in template_xml.findall("transition"):
        source = trans_xml.find("source").get("ref")
        target = trans_xml.find("target").get("ref")
        tid = trans_xml.get("id")
        guard = update = sync = select = None

        for label in trans_xml.findall("label"):
            kind = label.get("kind")
            if kind == "guard":
                guard = label.text
            elif kind == "assignment":
                update = label.text
            elif kind == "synchronisation":
                sync = label.text
            elif kind == "select":
                select = label.text

        template.transitions.append(
            Transition(tid, source, target, guard, update, sync, select)
        )

    return template


def _channel_param_mapping(tmpl, args):
    return {
        param: normalize_channel_name(arg)
        for param, arg in zip(tmpl.parameters, args)
        if tmpl.parameter_kinds.get(param) == "channel"
    }


def analyze_communications(nta):
    """
    Resolve sync labels across all instances using parameter mapping.

    Returns list of tuples:
        (sorted sender list, sorted receiver list, channel_name)
    """

    tmpl_by_name = {template.name: template for template in nta.templates}
    senders = {}
    receivers = {}

    for inst_name, (tmpl_name, args) in nta.instances.items():
        tmpl = tmpl_by_name.get(tmpl_name)
        if not tmpl:
            continue

        mapping = _channel_param_mapping(tmpl, args)
        for trans in tmpl.transitions:
            direction, actual, _ = resolve_sync_label(trans.sync, mapping)
            if not direction or not actual:
                continue

            if direction == "send":
                senders.setdefault(actual, set()).add(inst_name)
            else:
                receivers.setdefault(actual, set()).add(inst_name)

    comms = []
    for chan in sorted(set(senders) | set(receivers)):
        s_list = sorted(senders.get(chan, {"(unknown)"}))
        r_list = sorted(receivers.get(chan, {"(unknown)"}))
        comms.append((s_list, r_list, chan))
    return comms


if __name__ == "__main__":
    import sys

    xml_file = sys.argv[1] if len(sys.argv) > 1 else "xml\\.xml"
    tree = ET.parse(xml_file)
    root = tree.getroot()

    nta = NTA()
    nta.channels = parse_channels(root)
    nta.instances = parse_instances(get_system_text(root))

    for template_xml in root.findall("template"):
        nta.templates.append(parse_template(template_xml))

    for template in nta.templates:
        print(template)

    print("\n" + "=" * 50)
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
            for sender in s_list:
                for receiver in r_list:
                    print(f"  {sender} --> {receiver}  via [{channel}]")
    else:
        print("  (no synchronisations found)")
