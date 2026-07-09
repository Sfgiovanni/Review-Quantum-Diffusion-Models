from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

path = Path("notebooks/01_reproducible_literature_search.ipynb")
nb = nbformat.read(path, as_version=4)
ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
ep.preprocess(nb, {"metadata": {"path": "."}})
nbformat.write(nb, path)
