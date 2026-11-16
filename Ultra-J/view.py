"""Compatible CLI for ULTRA-J UI compilation; implementation lives in ui/."""
from ui import compile_view, compile_view_rules, main, stylesheet

__all__ = ["compile_view", "compile_view_rules", "stylesheet", "main"]

if __name__ == "__main__":
    main()
