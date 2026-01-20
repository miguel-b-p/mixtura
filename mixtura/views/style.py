"""
ANSI terminal styling for Mixtura.

Provides color constants and the ASCII logo.
"""


class Style:
    """ANSI escape codes for terminal styling."""
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Logo Palette -> Semantic Names
    ERROR = "\033[38;2;255;110;199m"     # Soup Pink
    SUCCESS = "\033[38;2;120;220;180m"   # Mint/Rainbow
    WARNING = "\033[38;2;210;160;100m"   # Wood/Gold
    INFO = "\033[38;2;100;200;255m"      # Sparkle Blue
    MAIN = "\033[38;2;200;160;255m"      # Lavender/Mix

    ASCII = f"""{MAIN}
    ▙▗▌ ▗      ▐              
    ▌▘▌ ▄  ▚▗▘ ▜▀  ▌ ▌ ▙▀▖ ▝▀▖
    ▌ ▌ ▐  ▗▚  ▐ ▖ ▌ ▌ ▌   ▞▀▌
    ▘ ▘ ▀▘ ▘ ▘  ▀  ▝▀▘ ▘   ▝▀▘
{RESET}"""
