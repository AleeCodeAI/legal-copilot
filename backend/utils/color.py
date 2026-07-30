import logging

class Logger:

    # Foreground colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;213m'
    PURPLE = '\033[38;5;93m'
    TEAL = '\033[38;5;37m'
    GOLD = '\033[38;5;220m'
    LIME = '\033[38;5;118m'
    SKY_BLUE = '\033[38;5;117m'
    TURQUOISE = '\033[38;5;80m'
    SALMON = '\033[38;5;209m'
    VIOLET = '\033[38;5;177m'
    GRAY = '\033[38;5;245m'
    LIGHT_GRAY = '\033[38;5;250m'
    
    # Background color
    BG_BLACK = '\033[40m'
    
    # Reset code to return to default color
    RESET = '\033[0m'

    name: str = ""
    color: str = '\033[37m'

    def log(self, message):
        """
        Log this as an info message, identifying the agent
        """
        color_code = self.BG_BLACK + self.color
        message = f"[{self.name}] {message}"
        logging.info(color_code + message + self.RESET)