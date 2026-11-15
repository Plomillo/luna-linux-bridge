try:
    from .cli import main
except ImportError:
    from cli import main

raise SystemExit(main())

