# Inteligência do mercado austríaco de empregos em dados

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Resumo

Este projeto analisa a procura de profissionais de dados na Áustria e compara essa procura com sinais públicos de oferta de candidatos. O foco é apoiar decisões de carreira e portfólio, com atenção especial à Estíria e comparação com Viena. A análise combina anúncios de emprego, séries oficiais e projetos públicos no GitHub.

O retrato de anúncios tem uma data de referência específica: 18 de outubro de 2026. Foram identificados 10.655 anúncios únicos; 699 anúncios de oito famílias de funções compõem o conjunto principal. SQL aparece em 40% e Python em 39% dos anúncios principais. Viena concentra 45% deles; a Estíria, 62 dos 699. Esses números descrevem um retrato de anúncios, não contratações ou fluxo anual de vagas.

A análise também compara competências citadas pelos empregadores com evidências em perfis públicos. Essa comparação usa populações diferentes e deve ser lida como indicação de lacunas relativas, não como uma razão exata entre vagas e candidatos. O perfil pessoal permanece privado; o repositório público usa um perfil neutro de exemplo.

## O que o projeto demonstra

- Pipeline Python para normalização, classificação por regras e deduplicação de anúncios.
- Séries oficiais do AMS e Eurostat, além de análises agregadas de oferta pública.
- Auditorias de precisão, intervalos de Wilson e regressão salarial controlada.
- Exportação pública com verificações para impedir a publicação de dados privados ou identificáveis.

## Limites essenciais

A procura é uma fotografia de anúncios disponíveis em um dia, não uma série anual de vagas ou contratações. A cobertura não inclui grandes páginas de carreira corporativas; salários anunciados são frequentemente pisos de convenções coletivas. Perfis públicos não mostram competências, experiência ou trabalho privado. O projeto não faz alegações causais.

## Explorar e reproduzir

O [README completo em inglês](README.md) inclui gráficos, fontes, metodologia, limitações e comandos. Para detalhes de execução, consulte também [metodologia](docs/methodology.md) e [fontes de dados](docs/data-sources.md).

[Repositório](https://github.com/RafaelBraga-Kribitz/austria-data-job-market-intelligence) · [Quadro de decisões visuais](docs/visual-decision-board.md) · [Limitações](docs/limitations.md)
