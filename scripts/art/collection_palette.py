"""Turns a theme's colors into a Windows Terminal color scheme."""

ANSI = ["black", "red", "green", "yellow", "blue", "purple", "cyan", "white",
        "brightBlack", "brightRed", "brightGreen", "brightYellow", "brightBlue", "brightPurple", "brightCyan", "brightWhite"]


def palette(name, bg, fg, cursor, selection, colors):
    """`colors`: the 16 ANSI colors, in order, as one string of hex values."""
    values = colors.split()
    assert len(values) == 16, name
    return {"name": f"Claude · {name}", "background": bg, "foreground": fg, "cursorColor": cursor, "selectionBackground": selection,
            **dict(zip(ANSI, values))}
