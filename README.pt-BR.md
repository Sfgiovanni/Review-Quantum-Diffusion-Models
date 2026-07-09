# Busca Bibliográfica de Quantum Diffusion Models

Este repositório contém um pipeline reprodutível para buscar literatura sobre **Quantum Diffusion Models**.

Os registros de escopo IEEE e Springer são recuperados pelo Crossref usando restrições por prefixo DOI (`10.1109` e `10.1007`). O projeto não afirma acesso direto às APIs proprietárias IEEE Xplore ou Springer Nature.

## Uso rápido

```bash
python -m venv .venv
source .venv/bin/activate
make install
make smoke-test
python -m quantum_diffusion_search all --config configs/search_config.yaml
```

## Saídas principais

- `data/processed/all_source_records.csv`
- `data/processed/deduplicated_records.csv`
- `data/processed/relevant_candidates.xlsx`
- `data/processed/screening_template.xlsx`
- `reports/search_report.md`
- `reports/methods_text.md`
- `data/raw/<run_id>/run_manifest.json`

## Reprodução

Reprodução exata usa respostas brutas congeladas:

```bash
python -m quantum_diffusion_search reproduce --raw-run data/raw/<run_id>
```

Atualização de busca consulta as APIs novamente:

```bash
python -m quantum_diffusion_search update-search --config configs/search_config.yaml
```

O score automático serve apenas para priorização. A inclusão final depende de triagem humana.
