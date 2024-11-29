import anyio

from . import server


def main():
    """Main entry point for the package."""
    anyio.run(server.main)

# Optionally expose other important items at package level
__all__ = ['main', 'server']