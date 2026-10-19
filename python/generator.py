"""
maspy_generator.py

Generate MASPY agents from a channel-centric reading of UPPAAL models.
Temporal elements such as clocks, invariants, and time-driven transitions are
intentionally ignored for now.
"""

from collections import defaultdict
import os
import re
import sys
import xml.etree.ElementTree as ET

from xmlparser import (
    NTA,
    get_system_text,
    normalize_channel_name,
    parse_channels,
    parse_instances,
    parse_template,
    resolve_sync_label,
)


def _py_val(raw):
    raw = raw.strip()
    if raw.lower() == "false":
        return '"false"'
    if raw.lower() == "true":
        return '"true"'
    return raw


def _belief_add_expr(name, value, adds_event=False):
    return f'Belief("{name}", {value}, adds_event={adds_event})'


def _context_expr(context_args):
    if not context_args:
        return ""
    if len(context_args) == 1:
        return context_args[0]
    return "[" + ", ".join(context_args) + "]"


def _references_any_var(text, names):
    if not text or not names:
        return False

    return any(re.search(rf"\b{re.escape(name)}\b", text) for name in names)


def _bool_params(tmpl):
    return [
        param for param in tmpl.parameters
        if tmpl.parameter_kinds.get(param) == "bool"
    ]


def _state_variables(tmpl, temporal_vars):
    variables = {
        param: {"kind": "bool", "initial": "false"}
        for param in _bool_params(tmpl)
    }

    for var_name, var_info in tmpl.variables.items():
        if var_name not in temporal_vars:
            variables[var_name] = var_info

    return variables


def _infer_temporal_vars(tmpl):
    temporal_vars = set(tmpl.temporal_vars)
    int_vars = {
        var_name
        for var_name, var_info in tmpl.variables.items()
        if var_info.get("kind") == "int"
    }

    for trans in tmpl.transitions:
        for var_name in int_vars:
            if (
                trans.guard
                and re.search(
                    rf"\b{re.escape(var_name)}\b\s*(?:<=|>=|<|>)",
                    trans.guard,
                )
            ):
                temporal_vars.add(var_name)

            if (
                trans.update
                and re.search(rf"\b{re.escape(var_name)}\b\s*(?:\+\+|--)", trans.update)
            ):
                temporal_vars.add(var_name)

    return temporal_vars


def _channel_param_map(tmpl, args):
    return {
        param: normalize_channel_name(arg)
        for param, arg in zip(tmpl.parameters, args)
        if tmpl.parameter_kinds.get(param) == "channel"
    }


def guard_to_context(guard, temporal_vars):
    """
    Translate only non-temporal guards into MASPY context.

    Supported examples:
      !activated
      activated
      activated == true
      activated == false
    """

    if not guard:
        return [], [], False, False

    context_args = []
    comment_lines = []
    has_supported_guard = False
    has_temporal_guard = False

    parts = re.split(r"\band\b|&&|\n", guard)
    for part in parts:
        clause = part.strip()
        if not clause:
            continue

        if _references_any_var(clause, temporal_vars):
            comment_lines.append(f"# temporal guard ignored: {clause}")
            has_temporal_guard = True
            continue

        negation = re.match(r"^!(\w+)$", clause)
        if negation:
            context_args.append(f'Belief("{negation.group(1)}", "false")')
            has_supported_guard = True
            continue

        bare_name = re.match(r"^(\w+)$", clause)
        if bare_name:
            context_args.append(f'Belief("{bare_name.group(1)}", "true")')
            has_supported_guard = True
            continue

        bool_equality = re.match(
            r"^(\w+)\s*==\s*(true|false)$", clause, re.IGNORECASE
        )
        if bool_equality:
            context_args.append(
                f'Belief("{bool_equality.group(1)}", '
                f'{_py_val(bool_equality.group(2))})'
            )
            has_supported_guard = True
            continue

        value_equality = re.match(r"^(\w+)\s*==\s*(-?\d+)$", clause)
        if value_equality:
            context_args.append(
                f'Belief("{value_equality.group(1)}", {value_equality.group(2)})'
            )
            has_supported_guard = True
            continue

        comment_lines.append(f"# guard not translated: {clause}")

    return context_args, comment_lines, has_supported_guard, has_temporal_guard


def update_to_body(update, indent, state_variables, temporal_vars):
    """
    Translate only non-temporal variable updates into MASPY beliefs.
    """

    if not update:
        return [], [], False, False

    body_lines = []
    comment_lines = []
    has_supported_update = False
    has_temporal_update = False
    state_var_set = set(state_variables)

    parts = re.split(r",|\n", update)
    for part in parts:
        clause = part.strip()
        if not clause:
            continue

        if _references_any_var(clause, temporal_vars):
            comment_lines.append(f"{indent}# temporal update ignored: {clause}")
            has_temporal_update = True
            continue

        assignment = re.match(r"^(\w+)\s*=\s*(.+)$", clause)
        if assignment and assignment.group(1) in state_var_set:
            var_name = assignment.group(1)
            body_lines.append(
                f'{indent}self._set_belief("{var_name}", '
                f"{_py_val(assignment.group(2))})"
            )
            has_supported_update = True
            continue

        comment_lines.append(f"{indent}# update not translated: {clause}")

    return body_lines, comment_lines, has_supported_update, has_temporal_update


def select_to_body(select, indent):
    if not select:
        return [], []

    body_lines = []
    comment_lines = []
    matches = list(
        re.finditer(r"(\w+)\s*:\s*int\s*\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", select)
    )

    for int_range in matches:
        var_name, min_value, max_value = int_range.groups()
        body_lines.append(
            f"{indent}{var_name} = random.randint({min_value}, {max_value})"
        )

    if not matches:
        comment_lines.append(f"{indent}# select not translated: {select.strip()}")

    return body_lines, comment_lines


def _location_name(loc_by_id, loc_id):
    loc = loc_by_id.get(loc_id)
    return loc.name if loc and loc.name else loc_id


def _should_skip_transition(trans, guard_meta, update_meta):
    _, _, has_supported_guard, has_temporal_guard = guard_meta
    _, _, has_supported_update, has_temporal_update = update_meta

    if trans.sync:
        return False

    if (
        trans.source == trans.target
        and not has_supported_guard
        and not has_supported_update
    ):
        return True

    return False


def build_nta(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    nta = NTA()
    nta.channels = parse_channels(root)
    nta.instances = parse_instances(get_system_text(root))

    for template_xml in root.findall("template"):
        nta.templates.append(parse_template(template_xml))

    return nta


def _build_channel_receivers(nta):
    tmpl_by_name = {template.name: template for template in nta.templates}
    receivers = {}

    for inst_name, (tmpl_name, args) in nta.instances.items():
        tmpl = tmpl_by_name.get(tmpl_name)
        if not tmpl:
            continue

        param_map = _channel_param_map(tmpl, args)
        for trans in tmpl.transitions:
            direction, actual_channel, _ = resolve_sync_label(trans.sync, param_map)
            if direction == "receive" and actual_channel:
                receivers.setdefault(actual_channel, set()).add(inst_name)

    return {
        channel: sorted(instances)
        for channel, instances in receivers.items()
    }


def generate_instance_class(inst_name, tmpl, param_map, chan_receivers):
    indent = "    "
    inner_indent = "        "

    loc_by_id = {loc.id: loc for loc in tmpl.locations}
    temporal_vars = _infer_temporal_vars(tmpl)
    state_variables = _state_variables(tmpl, temporal_vars)

    init_name = _location_name(loc_by_id, tmpl.init)

    transitions_by_source = defaultdict(list)
    for trans in tmpl.transitions:
        transitions_by_source[trans.source].append(trans)

    active_state_ids = set()
    for src_id, transitions in transitions_by_source.items():
        for trans in transitions:
            guard_meta = guard_to_context(trans.guard, temporal_vars)
            update_meta = update_to_body(
                trans.update, inner_indent, state_variables, temporal_vars
            )
            if _should_skip_transition(trans, guard_meta, update_meta):
                continue

            direction, _, _ = resolve_sync_label(trans.sync, param_map)
            if direction != "receive":
                active_state_ids.add(src_id)

    lines = []
    lines.append(f"class {inst_name}(Agent):")
    lines.append(f"{indent}def __init__(self, agt_name=None):")
    lines.append(f"{inner_indent}super().__init__(agt_name)")
    lines.append(f"{inner_indent}self._transition_count = 0")
    lines.append("")

    for var_name, var_info in state_variables.items():
        lines.append(
            f"{inner_indent}self.add("
            f"{_belief_add_expr(var_name, _py_val(var_info.get('initial', 'false')))}"
            f")"
        )

    lines.append("")
    lines.append(f"{indent}def _set_belief(self, name, value):")
    lines.append(f"{inner_indent}for belief in list(self.belief_list):")
    lines.append(
        f'{inner_indent}{indent}if belief.name == name and belief.source == "self":'
    )
    lines.append(f"{inner_indent}{indent}{indent}self.rm(belief)")
    lines.append(f"{inner_indent}self.add(Belief(name, value, adds_event=False))")
    lines.append("")
    lines.append(f"{indent}def _begin_transition(self):")
    lines.append(
        f"{inner_indent}if self._transition_count >= MAX_AGENT_TRANSITIONS:"
    )
    lines.append(
        f'{inner_indent}{indent}self.print("Maximum transition limit reached")'
    )
    lines.append(f"{inner_indent}{indent}Admin().stop_system()")
    lines.append(f"{inner_indent}{indent}return False")
    lines.append(f"{inner_indent}self._transition_count += 1")
    lines.append(f"{inner_indent}return True")
    lines.append("")
    lines.append(f"{indent}def load_initial_goal(self):")
    lines.append(f'{inner_indent}self._set_belief("__state", "{init_name}")')
    if tmpl.init in active_state_ids:
        lines.append(f'{inner_indent}self.add(Goal("{init_name}"))')

    lines.append("")

    generated_plans = 0

    for src_id, transitions in transitions_by_source.items():
        src_name = _location_name(loc_by_id, src_id)

        plan_counter = 0
        for trans in transitions:
            guard_meta = guard_to_context(trans.guard, temporal_vars)
            update_meta = update_to_body(
                trans.update, inner_indent, state_variables, temporal_vars
            )
            if _should_skip_transition(trans, guard_meta, update_meta):
                continue

            tgt_name = _location_name(loc_by_id, trans.target)
            is_self_loop = trans.source == trans.target

            context_args = [f'Belief("__state", "{src_name}")']
            comment_lines = []
            trigger_goal = f'Goal("{src_name}")'

            direction, actual_channel, _ = resolve_sync_label(trans.sync, param_map)
            if direction == "receive" and actual_channel:
                trigger_goal = f'Goal("{actual_channel}")'

            guard_ctx, guard_comments, _, _ = guard_meta
            context_args.extend(guard_ctx)
            comment_lines.extend(guard_comments)

            plan_counter += 1
            suffix = f"_{plan_counter}" if len(transitions) > 1 else ""
            plan_name = f"{src_name}{suffix}"

            context_expr = _context_expr(context_args)
            if context_expr:
                lines.append(f"{indent}@pl(gain, {trigger_goal}, {context_expr})")
            else:
                lines.append(f"{indent}@pl(gain, {trigger_goal})")

            for comment in comment_lines:
                lines.append(f"{indent}{comment}")

            lines.append(f"{indent}def {plan_name}(self, src, *plan_args):")
            lines.append(f"{inner_indent}if not self._begin_transition():")
            lines.append(f"{inner_indent}{indent}return")

            trace_parts = [
                f"State: {src_name} (self-loop)"
                if is_self_loop else f"{src_name} -> {tgt_name}"
            ]
            if direction and actual_channel:
                sync_direction = "sending" if direction == "send" else "receiving"
                trace_parts.append(f"sync {sync_direction}: {actual_channel}")

            body_lines = [
                f'{inner_indent}self.print(" | ".join({trace_parts!r}))'
            ]

            select_lines, select_comments = select_to_body(trans.select, inner_indent)
            body_lines.extend(select_lines)
            body_lines.extend(select_comments)

            update_lines, update_comments, _, _ = update_meta
            body_lines.extend(update_lines)
            body_lines.extend(update_comments)

            if direction == "send" and actual_channel:
                receiver_names = chan_receivers.get(actual_channel, [])
                targets = [target for target in receiver_names if target != inst_name]
                if not targets:
                    targets = receiver_names

                if targets:
                    for target in targets:
                        body_lines.append(
                            f'{inner_indent}self.send("{target}", achieve, '
                            f'Goal("{actual_channel}"), "{actual_channel}")'
                        )
                else:
                    body_lines.append(
                        f"{inner_indent}# receiver not identified for channel: "
                        f"{actual_channel}"
                    )

            if not is_self_loop:
                body_lines.append(
                    f'{inner_indent}self._set_belief("__state", "{tgt_name}")'
                )

            if trans.target in active_state_ids:
                body_lines.append(f'{inner_indent}self.add(Goal("{tgt_name}"))')

            if not body_lines:
                body_lines.append(f"{inner_indent}pass")

            lines.extend(body_lines)
            lines.append("")
            generated_plans += 1

    if generated_plans == 0:
        lines.append(f"{indent}# No channel-centric plans were generated.")
        lines.append("")

    return "\n".join(lines)


def generate_maspy_file(nta):
    tmpl_by_name = {template.name: template for template in nta.templates}
    chan_receivers = _build_channel_receivers(nta)

    output = []
    output.append("import random")
    output.append("from maspy import *")
    output.append("MAX_AGENT_TRANSITIONS = 50")

    for inst_name, (tmpl_name, args) in nta.instances.items():
        tmpl = tmpl_by_name.get(tmpl_name)
        if not tmpl:
            output.append(f"# Warning: template '{tmpl_name}' not found")
            continue

        param_map = _channel_param_map(tmpl, args)

        output.append("# " + "-" * 60)
        output.append(f"# Instance: {inst_name} (template: {tmpl_name})")
        output.append("# " + "-" * 60)
        output.append(
            generate_instance_class(
                inst_name,
                tmpl,
                param_map,
                chan_receivers,
            )
        )

    output.append('if __name__ == "__main__":')
    agent_vars = []
    for inst_name in nta.instances:
        agent_var = inst_name.lower()
        agent_vars.append(agent_var)
        output.append(f'    {agent_var} = {inst_name}("{inst_name}")')

    if nta.channels:
        channel_vars = []
        for channel in nta.channels:
            channel_var = f'{channel.name.lower()}_channel'
            channel_vars.append(channel_var)
            output.append(f'    {channel_var} = Channel("{channel.name}")')

        agents_list = ", ".join(agent_vars)
        channels_list = ", ".join(channel_vars)
        output.append(
            f"    Admin().connect_to([{agents_list}], [{channels_list}])"
        )

    for agent_var in agent_vars:
        output.append(f"    {agent_var}.load_initial_goal()")

    output.append("    Admin().start_system()")
    output.append("")

    return "\n".join(output)


if __name__ == "__main__":
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "xml\\light-switch.xml"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "python\\"

    nta = build_nta(xml_file)
    code = generate_maspy_file(nta)

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(xml_file))[0]
    out_file = os.path.join(out_dir, f"{base}_agents.py")

    with open(out_file, "w", encoding="utf-8") as output_file:
        output_file.write(code)

    print(f"Generated file: {out_file}")
