import icdiff
from prettyprinter import install_extras, pformat

install_extras()


def pretty_compare(config, op, left, right):
    very_verbose = config.option.verbose >= 2
    if not very_verbose:
        return None

    if op != "==":
        return None

    try:
        if abs(left + right) < 100:
            return None
    except TypeError:
        pass

    try:
        pretty_left = pformat(
            left, indent=4, width=80, sort_dict_keys=True
        ).splitlines()
        pretty_right = pformat(
            right, indent=4, width=80, sort_dict_keys=True
        ).splitlines()
        differ = icdiff.ConsoleDiff(cols=160, tabsize=4)
        icdiff_lines = list(
            differ.make_table(pretty_left, pretty_right, context=False)
        )

        return (
            ["equals failed"]
            + ["<left>".center(79) + "|" + "<right>".center(80)]
            + ["-" * 160]
            + [icdiff.color_codes["none"] + l for l in icdiff_lines]
        )
    except Exception:
        return None


def pytest_assertrepr_compare(config, op, left, right):
    return pretty_compare(config, op, left, right)