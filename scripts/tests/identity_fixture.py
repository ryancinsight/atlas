"""Input-sensitive source-identity fixtures shared by hook tests."""

PASSTHROUGH_IDENTITY: str = (
    "import os, subprocess, sys\n"
    "argv = sys.argv[1:]\n"
    "cwd = argv[argv.index('--command-cwd') + 1]\n"
    "command = [os.environ.get('CARGO', 'cargo') if value == 'cargo' else value\n"
    "           for value in argv[argv.index('--') + 1:]]\n"
    "raise SystemExit(subprocess.run(command, cwd=cwd).returncode)\n"
)
