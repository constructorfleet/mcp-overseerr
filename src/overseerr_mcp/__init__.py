from . import server

def main():
    """Entry point for the overseerr-mcp command.
    """
    server.main()

# Optionally expose other important items at package level
__all__ = ['main', 'server']