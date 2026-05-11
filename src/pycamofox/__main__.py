import sys

if len(sys.argv) >= 2 and sys.argv[1] == "daemon":
    import argparse
    parser = argparse.ArgumentParser(prog="pycamofox daemon")
    parser.add_argument("--port", type=int, default=9377)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--storage-dir", type=str, default=None)
    parser.add_argument(
        "--stealth",
        type=str,
        default="default",
        choices=["none", "default", "compatible", "maximum"],
        help="Stealth mode: none (no hooks), default (basic), compatible (tested hooks), maximum (all hooks)",
    )
    args = parser.parse_args(sys.argv[2:])

    from pycamofox.daemon.server import run_server
    run_server(
        port=args.port,
        headless=args.headless,
        storage_dir=args.storage_dir,
        stealth=args.stealth,
    )
else:
    from pycamofox.cli import main
    main()