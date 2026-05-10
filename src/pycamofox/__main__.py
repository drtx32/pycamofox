import sys

if len(sys.argv) >= 2 and sys.argv[1] == "daemon":
    import argparse
    parser = argparse.ArgumentParser(prog="pycamofox daemon")
    parser.add_argument("--port", type=int, default=9377)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--storage-dir", type=str, default=None)
    args = parser.parse_args(sys.argv[2:])

    from pycamofox.daemon.server import run_server
    run_server(port=args.port, headless=args.headless, storage_dir=args.storage_dir)
else:
    from pycamofox.cli import main
    main()