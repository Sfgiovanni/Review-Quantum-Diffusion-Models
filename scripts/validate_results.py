import sys

from quantum_diffusion_search.cli import main

raise SystemExit(main(["validate", "--run-id", sys.argv[1]]))
