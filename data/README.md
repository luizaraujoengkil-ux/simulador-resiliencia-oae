# data/

Pasta para arquivos de dados locais (KMZ, KML, CSV, XLSX) que você queira manter versionados junto com o projeto.

## Como usar

1. Copie seus arquivos para esta pasta (ex.: `data/oaes_vitoria.kmz`, `data/pontes_es.kml`).
2. Suba pro Git:
   ```powershell
   git add data/
   git commit -m "Adiciona base de OAEs de <cidade>"
   git push
   ```
3. No app, use o botão **"Carregar arquivo"** na sidebar e selecione o arquivo daqui (ou faça upload de outra máquina).

## Observações

- Esta pasta **não substitui** a base de demonstração (`sample_data/oae_teste.csv`) — ela é só um espaço para você guardar suas próprias bases.
- O `.gitignore` **não ignora** esta pasta, então tudo aqui vai pro GitHub. Se algum arquivo for sensível/sigiloso, **não coloque aqui** (use upload manual durante a sessão).
- Formatos aceitos pelo app:
  - **CSV** / **XLSX** — colunas `Latitude` e `Longitude` obrigatórias
  - **KML** / **KMZ** — `Placemark` com `Point` contendo coordenadas
