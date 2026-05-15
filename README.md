# Simulador de Resiliência da Rede Viária — Interdição de OAEs

Aplicativo **Streamlit** para análise de impacto da interdição de **OAEs (Obras de Arte Especiais)** — pontes e viadutos — sobre a rede viária. Permite carregar uma base de OAEs, visualizar a criticidade em mapa interativo, simular o fechamento de uma ou mais obras e comparar **rota original × rota alternativa**, com indicadores de impacto.

## ✨ Recursos

- Carregamento de bases nos formatos **CSV, XLSX, KML e KMZ**.
- Padronização automática de nomes de colunas (aceita variações como `lat`, `lng`, `nota`, etc.).
- **Base de demonstração** embutida para uso imediato sem upload.
- Mapa interativo (Folium) com cores por nota de criticidade.
- Simulação de interdição com **dois modos**:
  - **OSM (rede real)** via `osmnx` + `networkx`.
  - **Modo simplificado** (fallback) caso o OSM falhe / sem internet.
- Cards de indicadores: total de OAEs, interditadas, distância original, alternativa, aumento absoluto e percentual, status da rede.

## 🚀 Como rodar localmente

Pré-requisitos: Python 3.10+.

```bash
git clone https://github.com/<seu-usuario>/simulador-oae.git
cd simulador-oae

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

O app abre em `http://localhost:8501`. Sem nenhum upload, ele já roda com a base de demonstração.

## ☁️ Como publicar no Streamlit Community Cloud

1. Crie um repositório no GitHub (por exemplo `simulador-oae`).
2. Suba todos os arquivos deste projeto:
   ```bash
   git init
   git add .
   git commit -m "Primeira versão do simulador de OAEs"
   git branch -M main
   git remote add origin https://github.com/<seu-usuario>/simulador-oae.git
   git push -u origin main
   ```
3. Acesse [share.streamlit.io](https://share.streamlit.io).
4. Conecte com sua conta do GitHub.
5. Clique em **Create app**.
6. Selecione o **repositório**, a branch **main** e o arquivo **`app.py`**.
7. Clique em **Deploy**.
8. Copie o link público gerado e compartilhe.

> Dica: caso o build no Streamlit Cloud demore demais por causa do `osmnx`/`geopandas`, basta usar o **modo simplificado** dentro do app — ele funciona sem essas dependências.

## 📄 Formato esperado da planilha

A base pode usar nomes variados (o app reconhece sinônimos):

| Campo final         | Variações aceitas                                              |
|---------------------|-----------------------------------------------------------------|
| `Código OAE`        | `codigo`, `código`, `nome`, `name`, `id`                       |
| `Latitude`          | `lat`, `y`                                                      |
| `Longitude`         | `lon`, `lng`, `long`, `x`                                       |
| `Nota Geral`        | `nota`, `criticidade`, `score`                                 |
| `Município / UF`    | `municipio`, `município`, `cidade`                              |
| `Rodovia / Trecho`  | `rodovia`, `trecho`                                             |
| `Tipo` *(opcional)* | `tipo`                                                          |

Regras:
- `Latitude` e `Longitude` são **obrigatórias**.
- Se faltar `Código OAE`, o app gera `OAE-001`, `OAE-002`, ...
- Se faltar `Nota Geral`, assume valor padrão **3**.
- `Município / UF` e `Rodovia / Trecho` ausentes ficam como `"Não informado"`.
- Linhas sem coordenadas válidas são descartadas.

## 🗺️ Como usar KML / KMZ

O app implementa um parser próprio (sem depender de `fiona`) baseado em `zipfile` + `xml.etree.ElementTree`:

- Extrai todos os `Placemark` com `Point` → vira uma linha por ponto.
- O `<name>` do Placemark vira `Código OAE`.
- Tags `ExtendedData` / `SimpleData` são incorporadas e passam pela mesma padronização de colunas (ex.: um campo `Nota` vira `Nota Geral`).
- KMZ é apenas um ZIP contendo um `.kml` — o app abre automaticamente o primeiro `.kml` (priorizando `doc.kml`).

## 🧪 Base de demonstração

Em [`sample_data/oae_teste.csv`](sample_data/oae_teste.csv) há 10 OAEs fictícias com coordenadas reais aproximadas no **Espírito Santo** (Vitória, Vila Velha, Serra, Cariacica, Guarapari e arredores).

Use o toggle **"Usar base de demonstração"** na barra lateral, ou simplesmente abra o app sem fazer upload.

Sugestão de teste rápido:
1. Origem: **OAE-001** (Vitória)
2. Destino: **OAE-006** (Guarapari)
3. Interdite: **OAE-002** (Viaduto Vila Velha) — uma obra intermediária.
4. Clique em **Executar simulação** e compare as rotas.

## ⚠️ Limitações desta versão protótipo

- O cálculo de rotas considera **apenas distância geométrica** (não há tempo de viagem nem capacidade de tráfego).
- O **modo simplificado** conecta apenas os pontos da base entre si — útil para demonstração, não para análise real.
- O download via OSM exige conexão à internet e pode demorar alguns segundos.
- Não há autenticação, banco de dados nem persistência entre sessões.

## 🔭 Próximos passos

- Considerar **tempo de viagem** e classificação funcional das vias.
- Importação de bases oficiais (DNIT, SIGO-OAE) e cruzamento com volume de tráfego.
- Cálculo de **resiliência sistêmica** (não só par origem-destino).
- Relatórios em PDF e exportação dos resultados.
- Camada de **autenticação** e gestão de usuários.
- Eventual integração com **IA/ML** para priorização de manutenção.

## 🛠️ Estrutura do projeto

```
simulador-oae/
├── app.py                      # aplicação Streamlit
├── requirements.txt            # dependências
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml             # tema e configuração do servidor
└── sample_data/
    └── oae_teste.csv           # base de demonstração
```
