def parse_int(val: str, name: str) -> int:
    try:
        return int(val)
    except:
        raise ValueError(
            f"Value '{val}' is not valid for '{name}' - an int is required.",
        )


def err_msg(msg: str) -> str:
    return f"<span class='error_msg'>{msg}</span>"


def success_msg(msg: str) -> str:
    return f"<span class='success_msg'>{msg}</span>"
