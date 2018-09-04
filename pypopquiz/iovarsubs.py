"""Variable substitution in the input data structure."""

from typing import Any, Iterable, Tuple, Union


def substitute_variables(data: dict) -> None:
    """Look for variable references, and substitute their values in the data structure."""
    for question in data["questions"]:
        if "variables" in question:
            var_dict = question["variables"]
            substitute_variables_in_dict(question, var_dict)


def substitute_variables_in_dict(elems: dict, var_dict: dict) -> None:
    """Iterate over items in the dictionary, substitute in each item."""
    for key, item in elems.items():
        if key == 'variables':
            continue
        substitute_variables_kernel(elems, key, item, var_dict)


def substitute_variables_in_list(lst: list, var_dict: dict) -> None:
    """Iterate over elements in the list, substitute in each item."""
    for i, item in enumerate(lst):
        substitute_variables_kernel(lst, i, item, var_dict)


def substitute_variables_kernel(parent: Union[dict, list], key: Any, item: Any, var_dict: dict) -> None:
    """Inspect item, iterate further or substitute variables ."""
    if isinstance(item, list):
        substitute_variables_in_list(item, var_dict)

    elif isinstance(item, dict):
        substitute_variables_in_dict(item, var_dict)

    elif isinstance(item, str):
        sub = get_substitute_variable(item, var_dict)
        if sub is not None:
            parent[key] = sub


def get_substitute_variable(val: str, var_dict: dict) -> Any:
    """Return substitution for variable reference in str, or None if it is not found."""
    var_marker = 'var:'
    if val.startswith(var_marker):
        var_name = val[len(var_marker):]

        if var_name in var_dict:
            return var_dict[var_name]

    return None
