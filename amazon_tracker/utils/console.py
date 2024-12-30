from colorama import init, Fore, Style

# Initialize colorama for Windows
init()

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL, return_str=False):
    """Print colored text using colorama
    If return_str is True, returns the colored string instead of printing it"""
    colored_text = f"{style}{color}{text}{Style.RESET_ALL}"
    if return_str:
        return colored_text
    print(colored_text)
