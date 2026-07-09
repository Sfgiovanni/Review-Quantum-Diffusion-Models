import sys

from quantum_diffusion_search.cli import main

raise SystemExit(main(["report", "--run-id", sys.argv[1]]))
