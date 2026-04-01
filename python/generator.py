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


def _references_any_var(text, names):
    if not text or not names:
        return False

    return any(re.search(rf"\b{re.escape(name)}\b", text) for name in names)


def _bool_params(tmpl):
    return [
        param for param in tmpl.parameters
        if tmpl.parameter_kinds.get(param) == "bool"
    ]


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

        comment_lines.append(f"# guard not translated: {clause}")

    return context_args, comment_lines, has_supported_guard, has_temporal_guard


def update_to_body(update, indent, bool_params, temporal_vars):
    """
    Translate only non-temporal boolean updates into MASPY beliefs.
    """

    if not update:
        return [], [], False, False

    body_lines = []
    comment_lines = []
    has_supported_update = False
    has_temporal_update = False
    bool_param_set = set(bool_params)

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
        if assignment and assignment.group(1) in bool_param_set:
            body_lines.append(
                f'{indent}self.add(Belief("{assignment.group(1)}", '
                f'{_py_val(assignment.group(2))}))'
            )
            has_supported_update = True
            continue

        comment_lines.append(f"{indent}# update not translated: {clause}")

    return body_lines, comment_lines, has_supported_update, has_temporal_update


def _should_skip_transition(trans, guard_meta, update_meta):
    _, _, has_supported_guard, has_temporal_guard = guard_meta
    _, _, has_supported_update, has_temporal_update = update_meta

    if trans.sync:
        return False

    if has_temporal_guard and not has_supported_guard:
        return True

    if has_temporal_update and not has_supported_guard and not has_supported_update:
        return True

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

    return {name: sorted(instances) for name, instances in receivers.items()}


def generate_instance_class(inst_name, tmpl, param_map, chan_receivers):
    indent = "    "
    inner_indent = "        "

    loc_by_id = {loc.id: loc for loc in tmpl.locations}
    bool_params = _bool_params(tmpl)
    temporal_vars = tmpl.temporal_vars

    init_loc = loc_by_id.get(tmpl.init)
    init_name = init_loc.name if init_loc and init_loc.name else tmpl.init

    lines = []
    lines.append(f"class {inst_name}(Agent):")
    lines.append(f"{indent}def __init__(self, agt_name):")
    lines.append(f"{inner_indent}super().__init__(agt_name)")
    lines.append("")

    for bool_param in bool_params:
        lines.append(f'{inner_indent}self.add(Belief("{bool_param}", "false"))')

    lines.append("")
    lines.append(f"{indent}def load_initial_goal(self):")
    lines.append(f'{inner_indent}self.add(Goal("{init_name}"))')

    lines.append("")

    transitions_by_source = defaultdict(list)
    for trans in tmpl.transitions:
        transitions_by_source[trans.source].append(trans)

    generated_plans = 0

    for src_id, transitions in transitions_by_source.items():
        src_loc = loc_by_id.get(src_id)
        src_name = src_loc.name if src_loc and src_loc.name else src_id

        plan_counter = 0
        for trans in transitions:
            guard_meta = guard_to_context(trans.guard, temporal_vars)
            update_meta = update_to_body(
                trans.update, inner_indent, bool_params, temporal_vars
            )
            if _should_skip_transition(trans, guard_meta, update_meta):
                continue

            tgt_loc = loc_by_id.get(trans.target)
            tgt_name = tgt_loc.name if tgt_loc and tgt_loc.name else trans.target
            is_self_loop = trans.source == trans.target

            context_args = []
            comment_lines = []

            direction, actual_channel, _ = resolve_sync_label(trans.sync, param_map)
            if direction == "receive" and actual_channel:
                context_args.append(f'Goal("{actual_channel}")')

            guard_ctx, guard_comments, _, _ = guard_meta
            context_args.extend(guard_ctx)
            comment_lines.extend(guard_comments)

            plan_counter += 1
            suffix = f"_{plan_counter}" if len(transitions) > 1 else ""
            plan_name = f"{src_name}{suffix}"

            if context_args:
                ctx_str = ", ".join(context_args)
                lines.append(
                    f'{indent}@pl(gain, Goal("{src_name}"), {ctx_str})'
                )
            else:
                lines.append(f'{indent}@pl(gain, Goal("{src_name}"))')

            for comment in comment_lines:
                lines.append(f"{indent}{comment}")

            lines.append(f"{indent}def {plan_name}(self, src, *plan_args):")

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

            update_lines, update_comments, _, _ = update_meta
            body_lines.extend(update_lines)
            body_lines.extend(update_comments)

            if direction == "send" and actual_channel:
                targets = [
                    target for target in chan_receivers.get(actual_channel, [])
                    if target != inst_name
                ]
                if not targets:
                    targets = chan_receivers.get(actual_channel, [])

                if targets:
                    for target in targets:
                        body_lines.append(
                            f'{inner_indent}self.send("{target}", achieve, '
                            f'Goal("{actual_channel}"), "{actual_channel}")'
                        )
                else:
                    body_lines.append(
                        f'{inner_indent}self.send("?", achieve, '
                        f'Goal("{actual_channel}"), "{actual_channel}")  '
                        f'# receiver not identified'
                    )

            if not is_self_loop:
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
    output.append('"""')
    output.append("MASPY agents generated from a channel-centric UPPAAL model.")
    output.append('"""')
    output.append("from maspy import *")
    output.append("")

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
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "xml\\example_1.xml"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "python\\"

    nta = build_nta(xml_file)
    code = generate_maspy_file(nta)

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(xml_file))[0]
    out_file = os.path.join(out_dir, f"{base}_agents.py")

    with open(out_file, "w", encoding="utf-8") as output_file:
        output_file.write(code)

    print(f"Generated file: {out_file}")
