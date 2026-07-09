# Methodology

This project implements a reproducible bibliographic search pipeline for quantum diffusion model literature. arXiv records are retrieved from the public arXiv API. IEEE- and Springer-scoped records are retrieved as Crossref metadata with DOI-prefix restrictions: `10.1109` for IEEE and `10.1007` for Springer.

The Crossref results are described as DOI-prefix scoped metadata and not as direct searches of IEEE Xplore or Springer Nature proprietary APIs.
