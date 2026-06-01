"""
Gerador do Manual de Uso do OAE-SIM (PDF), usando fpdf2.

Execute:  python gerar_manual.py
Saída:    MANUAL_OAE-SIM.pdf
"""

from datetime import datetime
from fpdf import FPDF

TEAL = (0, 224, 212)
DARK = (15, 27, 51)
GRAY = (120, 120, 130)
LIGHTBOX = (240, 244, 250)
CODEBOX = (28, 38, 60)


def _t(s: object) -> str:
    """Texto seguro para as fontes núcleo (Latin-1) do fpdf2."""
    s = str(s)
    rep = {
        "→": "->", "←": "<-", "≤": "<=", "≥": ">=", "≈": "~",
        "Δ": "D", "φ": "phi", "λ": "lambda", "√": "raiz", "Σ": "Soma",
        "—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
        "…": "...", "•": "-", " ": " ",
    }
    for a, b in rep.items():
        s = s.replace(a, b)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class Manual(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRAY)
        self.set_y(8)
        self.cell(0, 5, _t("OAE-SIM - Manual de Uso"), align="L")
        self.cell(0, 5, _t(f"pag. {self.page_no()}"), align="R")
        self.set_text_color(0, 0, 0)
        self.set_y(18)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 5, _t("Simulador de Resiliencia da Rede Viaria - OAE-SIM  -  "
                           "github.com/luizaraujoengkil-ux/simulador-resiliencia-oae"),
                  align="C")
        self.set_text_color(0, 0, 0)


pdf = Manual(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=16)
pdf.set_margins(18, 18, 18)


# ---------- helpers de layout ----------
def h1(txt):
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_fill_color(*TEAL)
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _t("  " + txt), fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2.5)


def h2(txt):
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 6, _t(txt), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(0.5)


def p(txt):
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 4.8, _t(txt))
    pdf.ln(1.2)


def bullet(txt, lvl=0):
    pdf.set_font("Helvetica", "", 10)
    x0 = 18 + lvl * 6
    pdf.set_x(x0)
    pdf.cell(4, 4.8, _t("-"))
    pdf.set_x(x0 + 4)
    pdf.multi_cell(0, 4.8, _t(txt))
    pdf.ln(0.6)


def kv(k, v):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(18)
    pdf.cell(48, 4.8, _t(k))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 4.8, _t(v))
    pdf.ln(0.4)


def formula(txt, expl=None):
    pdf.ln(0.5)
    pdf.set_fill_color(*LIGHTBOX)
    pdf.set_font("Courier", "", 9.5)
    for line in txt.split("\n"):
        pdf.set_x(20)
        pdf.cell(0, 5.5, _t("  " + line), fill=True, ln=True)
    if expl:
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*GRAY)
        pdf.set_x(20)
        pdf.multi_cell(0, 4.2, _t(expl))
        pdf.set_text_color(0, 0, 0)
    pdf.ln(1.5)


def nota(txt):
    pdf.set_fill_color(255, 247, 224)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 4.4, _t("  Nota: " + txt), fill=True)
    pdf.ln(1.5)


# ============================ CAPA ============================
pdf.add_page()
pdf.set_fill_color(*DARK)
pdf.rect(0, 0, 210, 80, style="F")
pdf.set_xy(18, 24)
pdf.set_text_color(*TEAL)
pdf.set_font("Helvetica", "B", 24)
pdf.cell(0, 12, _t("OAE-SIM"), ln=True)
pdf.set_x(18)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 15)
pdf.cell(0, 9, _t("Manual de Uso"), ln=True)
pdf.set_x(18)
pdf.set_font("Helvetica", "", 11)
pdf.cell(0, 7, _t("Simulador de Resiliencia da Rede Viaria - Interdicao de OAEs"), ln=True)
pdf.set_text_color(0, 0, 0)
pdf.ln(28)
pdf.set_font("Helvetica", "", 11)
kv("Autor:", "Luiz Araujo de Souza Junior")
kv("Contexto:", "ET 261400 - Ciencia de Dados e Aprendizado Profundo aplicados aos Transportes")
kv("Versao:", "OAE-SIM v0.1")
kv("Gerado em:", datetime.now().strftime("%d/%m/%Y"))
kv("Licenca:", "MIT")
pdf.ln(6)
p("Este manual explica, passo a passo, como operar o simulador; o que esperar "
  "matematicamente de cada calculo; e como interpretar os resultados na pratica. "
  "Use o sumario abaixo para navegar.")

h2("Sumario")
for i, t in enumerate([
    "1. O que e o simulador",
    "2. Conceitos-chave",
    "3. Primeiros passos (carregar dados)",
    "4. A interface (barra lateral e tela)",
    "5. Como usar - caso a caso",
    "6. O que esperar - a matematica por tras",
    "7. Como interpretar os resultados",
    "8. O relatorio PDF",
    "9. Boas praticas e dicas",
    "10. Limitacoes desta versao",
    "11. Solucao de problemas",
    "12. Glossario",
], 1):
    bullet(t)


# ============================ 1 ============================
pdf.add_page()
h1("1. O que e o simulador")
p("O OAE-SIM avalia o impacto da interdicao de Obras de Arte Especiais (OAEs) - "
  "pontes e viadutos - sobre a rede viaria. Para cada cenario, ele compara a "
  "ROTA ORIGINAL (rede intacta) com a ROTA ALTERNATIVA (apos fechar a obra) e "
  "quantifica o quanto a viagem fica mais longa.")
p("Em outras palavras, ele responde: 'se esta ponte for interditada, quanto a "
  "mais um veiculo que precisa atravessa-la teria que rodar?'. Quanto maior esse "
  "aumento, mais critica a obra para a conectividade local.")
h2("Para que serve")
bullet("Priorizar manutencao: identificar quais OAEs sao gargalos da rede.")
bullet("Planejar contingencia: saber se existe (e qual e) a rota alternativa.")
bullet("Comunicar risco: gerar relatorio PDF com mapas, graficos e ranking.")
nota("Esta versao mede impacto LOCAL (uma viagem que atravessa a obra), com "
     "distancia geometrica. Nao modela fluxo real de trafego nem tempo de viagem.")


# ============================ 2 ============================
h1("2. Conceitos-chave")
kv("OAE", "Obra de Arte Especial (ponte, viaduto, passarela). E o objeto da analise.")
kv("Interdicao", "Fechamento simulado da obra: as vias sobre/junto a ela sao removidas da rede.")
kv("OAE focal", "A obra principal do cenario - sempre incluida na interdicao. As rotas sao "
   "derivadas em torno dela.")
kv("Rota original", "Caminho mais curto entre origem e destino com a rede intacta.")
kv("Rota alternativa", "Caminho mais curto apos remover as vias da(s) OAE(s) interditada(s).")
kv("Origem/Destino", "Pontos sinteticos em lados opostos da OAE focal, derivados "
   "automaticamente (nao sao fluxos reais de O/D urbanos).")
kv("Criticidade", "Quanto a interdicao da OAE aumenta a distancia - indicador relativo de "
   "importancia da obra para a rede.")


# ============================ 3 ============================
h1("3. Primeiros passos (carregar dados)")
h2("3.1 Formatos aceitos")
bullet("Planilhas: CSV e XLSX.")
bullet("Geoespaciais: KML e KMZ (parser proprio; o <name> do Placemark vira o codigo da OAE).")
h2("3.2 Colunas (o app reconhece sinonimos)")
bullet("Obrigatorias: Latitude (lat, y) e Longitude (lon, lng, long, x).")
bullet("Codigo OAE (codigo, nome, id) - se faltar, gera OAE-001, OAE-002, ...")
bullet("Nota Geral (nota, criticidade, score) de 1 a 5 - se faltar, assume 3.")
bullet("Opcionais: Municipio/UF e Rodovia/Trecho (preenchidos por geocodificacao quando faltam).")
h2("3.3 Base de demonstracao")
p("Sem fazer upload, o app ja abre com uma base de exemplo (OAEs no Espirito Santo). "
  "Use o atalho na barra lateral para alternar entre a base demo e a sua.")
nota("Linhas sem coordenadas validas sao descartadas automaticamente.")


# ============================ 4 ============================
h1("4. A interface (barra lateral e tela)")
h2("4.1 Barra lateral - controles principais")
kv("Modo de calculo", "'Automatico (OSM -> simplificado se falhar)' usa a rede real do "
   "OpenStreetMap; 'Forcar modo simplificado' ignora o OSM (rede aproximada, sem internet).")
kv("Buffer (km)", "Margem ao redor da area de interesse (1 a 20 km). Define o tamanho da rede "
   "baixada. Recomendado 2-5 km; acima de ~10 km o download/calculo demora mais.")
kv("Mostrar malha", "Liga/desliga o desenho da rede viaria sobre o mapa geral.")
kv("Selecao de OAEs", "Escolha quais OAEs interditar; a primeira (ou a marcada) e a OAE focal.")
h2("4.2 Tela principal")
bullet("Mapa geral: todas as OAEs coloridas pela Nota Geral (criticidade estrutural).")
bullet("Cards de indicadores: distancias, aumento absoluto e percentual, status da rede.")
bullet("Comparativo de rotas: mapa com rota original (vermelha tracejada) e alternativa (verde).")
bullet("Relatorio consolidado: historico, ranking de manutencao e botao para gerar o PDF.")


# ============================ 5 ============================
pdf.add_page()
h1("5. Como usar - caso a caso")

h2("Caso A - Avaliar UMA ponte (interdicao simples)")
bullet("1. Carregue a base (ou use a demo).")
bullet("2. Na barra lateral, selecione a OAE a estudar (ela vira a focal).")
bullet("3. Ajuste o Buffer (comece com 3-5 km).")
bullet("4. Clique em 'Executar simulacao'.")
bullet("5. Leia os cards e veja o mapa: vermelho tracejado = rota original; verde = alternativa.")
p("Esperado: se houver desvio, a rota verde contorna a obra e os cards mostram o aumento "
  "de distancia (km e %). Se nao houver alternativa, o app avisa 'sem rota alternativa'.")

h2("Caso B - Comparar VARIAS pontes")
bullet("Rode o Caso A para cada OAE de interesse (uma por vez).")
bullet("Cada simulacao entra no historico da sessao.")
bullet("Ao final, o ranking de manutencao ordena as obras por prioridade.")
nota("Para ranqueamento puro de criticidade individual, interdite UMA OAE por vez.")

h2("Caso C - Multiplas interdicoes simultaneas")
bullet("Selecione 2+ OAEs na barra lateral antes de executar.")
bullet("Util para simular eventos (enchente, acidente) que fecham varias obras juntas.")
p("Esperado: o impacto tende a ser maior que a soma das interdicoes isoladas, pois "
  "a rede perde redundancia.")

h2("Caso D - Simulacao Geral (lote / Monte Carlo)")
bullet("Escolha a OAE focal e abra a 'Simulacao Geral - Configurar lote'.")
bullet("Defina a Profundidade (quantas OAEs entram junto da focal) e as Iteracoes.")
bullet("Escolha a Estrategia: Exaustiva, Amostra aleatoria ou Hibrida (recomendada).")
bullet("O app roda muitos cenarios e gera histograma, curva de degradacao e heatmap.")
p("Esperado: visao estatistica de como a rede degrada conforme mais OAEs sao fechadas "
  "junto com a focal, e quais 'parceiras' agravam mais o impacto.")

h2("Caso E - Sem internet / modo simplificado")
bullet("Marque 'Forcar modo simplificado' (ou o app cai nele se o OSM falhar).")
bullet("A rede vira uma aproximacao que liga as OAEs aos vizinhos mais proximos.")
nota("O modo simplificado serve para demonstracao; nao representa ruas reais.")

h2("Caso F - Gerar o relatorio PDF")
bullet("Apos rodar 1+ simulacoes, va em 'Relatorio consolidado'.")
bullet("Clique em 'Gerar relatorio completo em PDF' e depois em 'Baixar PDF gerado'.")
bullet("O PDF traz resumo, detalhamento, ranking, graficos e mapas (com fundo de rua real).")


# ============================ 6 ============================
pdf.add_page()
h1("6. O que esperar - a matematica por tras")

h2("6.1 Modelo de rede (grafo)")
p("A rede viaria e um grafo G = (V, E): V sao intersecoes (nos) e E sao trechos de via "
  "(arestas). Cada aresta tem um peso igual ao seu comprimento em metros.")

h2("6.2 Distancia geodesica (Haversine)")
formula(
    "a = sin^2(dphi/2) + cos(phi1)*cos(phi2)*sin^2(dlam/2)\n"
    "d = 2 * R * asin( raiz(a) ),   R = 6 371 000 m",
    "phi = latitude, lambda = longitude (em radianos); dphi e dlam sao as diferencas. "
    "Usada para distancias ponto-a-ponto e para dimensionar a area de interesse.")

h2("6.3 Caminho minimo (Dijkstra)")
p("As rotas (original e alternativa) sao o caminho de menor comprimento entre origem e "
  "destino, calculado pelo algoritmo de Dijkstra com o comprimento das vias como peso.")

h2("6.4 Interdicao = remocao cirurgica de arestas")
p("Para cada OAE interditada, todas as arestas cuja geometria passa a menos de 100 m do "
  "ponto da obra sao removidas do grafo. Remove-se a ARESTA (a via), nao o no - assim a "
  "estrutura da ponte e isolada sem desconectar as intersecoes vizinhas. A distancia "
  "ponto-via usa geometria (Shapely).")

h2("6.5 Origem e destino automaticos")
p("A partir da OAE focal, a origem e o no mais proximo (entre 200 m e 5 km) e o destino e "
  "o no na direcao mais OPOSTA (maior diferenca de azimute), garantindo uma travessia que "
  "passa pela obra.")
formula("azimute = atan2( y_no - y_oae , x_no - x_oae )",
        "O destino maximiza |azimute_origem - azimute_destino| (lados opostos da obra).")

h2("6.6 Indicadores de impacto")
formula(
    "aumento (km)  = (d_alt - d_orig) / 1000\n"
    "impacto (%)   = (d_alt - d_orig) / d_alt * 100\n"
    "fator (x)     = d_alt / d_orig",
    "d_orig = distancia da rota original; d_alt = distancia da rota alternativa. "
    "O impacto% fica entre 0% e ~100%; o fator diz quantas vezes a rota aumentou.")

h2("6.7 Area de interesse e raio")
p("O centro da area e o centroide das OAEs do cenario (na simulacao, inclui origem e "
  "destino). O raio = maior distancia do centro ate um ponto + Buffer (km), com minimo de "
  "1,5 km. E esse raio que define a rede baixada do OpenStreetMap.")

h2("6.8 Simulacao Geral (combinatoria / Monte Carlo)")
formula(
    "Exaustiva:  Soma_{k=0..P} C(n, k)        (todas as combinacoes ate a profundidade P)\n"
    "Amostra:    N cenarios sorteados (tamanho aleatorio)\n"
    "Hibrida:    todas as duplas/triplas + N sorteios para tamanhos maiores",
    "n = numero de OAEs co-candidatas; C(n,k) = combinacoes. A focal entra sempre. "
    "A curva de degradacao mostra o impacto medio/maximo em funcao de quantas OAEs sao "
    "fechadas juntas.")

h2("6.9 Priorizacao de manutencao (escore 0-100)")
formula(
    "s_estrutura = (6 - Nota) / 5            (Nota 1..5; nota baixa -> urgente)\n"
    "s_impacto   = Impacto_medio% / 100\n"
    "combinado   = 0,60*s_estrutura + 0,40*s_impacto\n"
    "Prioridade  = 100 / (1 + e^(-5*(combinado - 0,5)))    (sigmoide, 0..100)",
    "Combina condicao estrutural (peso 60%) e impacto na rede (peso 40%). "
    "Classes: ALTA (>=70), MEDIA (40-69), BAIXA (<40).")
p("Quando o scikit-learn esta disponivel, esse escore e produzido por uma rede neural "
  "MLP (topologia [2 -> 16 -> 8 -> 1]) treinada com dados sinteticos baseados na formula "
  "acima. No ambiente do Streamlit Cloud (Python 3.14), usa-se a HEURISTICA analitica "
  "equivalente (mesma formula 60/40 + sigmoide) - resultados praticamente identicos.")
nota("O modelo de prioridade foi treinado com dados sinteticos. Em producao, recomenda-se "
     "re-treinar com decisoes historicas reais de engenheiros de pontes.")


# ============================ 7 ============================
pdf.add_page()
h1("7. Como interpretar os resultados")
kv("Impacto baixo", "Existe rota alternativa proxima - a obra tem boa redundancia na rede.")
kv("Impacto alto", "O desvio e grande - a obra e um gargalo; candidata a prioridade alta.")
kv("Sem rota alternativa", "A interdicao desconecta o par O/D na area baixada - obra "
   "critica OU buffer pequeno demais (aumente o Buffer e teste de novo).")
kv("Fator (x)", "Quantas vezes a rota aumentou (ex.: 2,7x = quase tres vezes mais longa).")
kv("Baseline curta (*)", "Rota original < 1 km: o impacto% pode parecer extremo porque a "
   "base e curta. Priorize o aumento ABSOLUTO (km) e o fator nesses casos.")
kv("Modo OSM x simplificado", "Confie nos numeros do modo OSM (rede real). O simplificado "
   "e so demonstrativo.")
p("Regra pratica de leitura: olhe primeiro se HA rota alternativa; depois o aumento em km; "
  "depois o impacto% e o fator. Para decisao de manutencao, use o ranking de prioridade.")


# ============================ 8 ============================
h1("8. O relatorio PDF")
p("Gerado sob demanda (botao), o relatorio reune:")
bullet("Resumo executivo (cenarios com/sem alternativa, aumento medio e maximo).")
bullet("Detalhamento de todas as simulacoes da sessao (tabela).")
bullet("Priorizacao de manutencao (ranking 0-100, classes ALTA/MEDIA/BAIXA).")
bullet("Mapa de criticidade das OAEs (cor/tamanho = impacto medio).")
bullet("Histograma de impacto, curva de degradacao e heatmap de co-interdicao.")
bullet("Mapas de rota (ate 2 cenarios de maior impacto), com fundo de rua real, "
       "mostrando rota original (vermelha tracejada) x alternativa (verde).")
nota("Os mapas de rota saem para SIMULACOES INDIVIDUAIS (que guardam a geometria real "
     "calculada) e refletem exatamente o que apareceu na tela. Cenarios do lote entram "
     "nos graficos agregados. O fundo de rua real precisa de internet no momento de gerar "
     "o PDF; sem rede, o mapa sai sem o fundo.")


# ============================ 9 ============================
h1("9. Boas praticas e dicas")
bullet("Buffer: comece com 3-5 km. Se der 'sem rota alternativa', aumente (ate 20 km).")
bullet("Acima de ~10 km a rede OSM fica grande: download e calculo mais lentos.")
bullet("A 1a simulacao de uma area baixa o mapa do OSM; as seguintes reaproveitam o cache.")
bullet("Para criticidade individual, interdite uma OAE por vez.")
bullet("Para visao sistemica, use a Simulacao Geral (estrategia Hibrida).")
bullet("Gere o PDF so no final (ele e montado sob demanda para nao deixar a sessao lenta).")


# ============================ 10 ============================
h1("10. Limitacoes desta versao")
bullet("Usa distancia geometrica - nao ha tempo de viagem nem capacidade/volume de trafego.")
bullet("Origem e destino sao sinteticos (lados da obra), nao fluxos reais de O/D.")
bullet("Mede impacto LOCAL da obra, nao o impacto sistemico sobre viagens reais.")
bullet("O modo simplificado e apenas demonstrativo.")
bullet("Sem autenticacao, banco de dados ou persistencia entre sessoes.")


# ============================ 11 ============================
h1("11. Solucao de problemas")
kv("'Sem rota alternativa'", "Aumente o Buffer na barra lateral e rode de novo; ou escolha "
   "outra OAE focal.")
kv("'Nao consegui derivar O/D'", "A area baixada ficou pequena - aumente o Buffer.")
kv("OSM indisponivel", "Sem internet, marque 'Forcar modo simplificado' para continuar.")
kv("Tela 'Oh no / Error running app'", "Geralmente a instancia ficou sem memoria. Em "
   "'Manage app' use 'Reboot app' e aguarde 1-2 min.")
kv("Mapa de rota faltando no PDF", "So sai para simulacoes individuais (com geometria). "
   "Rode o cenario como simulacao individual.")
kv("Fundo de rua nao apareceu", "Precisa de internet ao gerar o PDF; sem rede, o mapa sai "
   "sem o fundo (apenas as rotas).")


# ============================ 12 ============================
h1("12. Glossario")
kv("OAE", "Obra de Arte Especial: ponte, viaduto, passarela.")
kv("Grafo / no / aresta", "Modelo da rede: nos = intersecoes; arestas = trechos de via.")
kv("Dijkstra", "Algoritmo do caminho de menor custo (aqui, menor comprimento).")
kv("Haversine", "Formula da distancia sobre a esfera terrestre.")
kv("Buffer", "Margem (km) ao redor da area que define o tamanho da rede baixada.")
kv("OSM", "OpenStreetMap: fonte da rede viaria real.")
kv("MLP", "Multi-Layer Perceptron: rede neural usada na priorizacao (com fallback heuristico).")
kv("Monte Carlo", "Geracao de muitos cenarios (aleatorios/combinatorios) para visao estatistica.")

pdf.ln(4)
pdf.set_font("Helvetica", "I", 8.5)
pdf.set_text_color(*GRAY)
pdf.multi_cell(0, 4.2, _t(
    "Documento gerado automaticamente para o OAE-SIM. Autor: Luiz Araujo de Souza Junior. "
    "Licenca MIT. Codigo: github.com/luizaraujoengkil-ux/simulador-resiliencia-oae"))
pdf.set_text_color(0, 0, 0)

out = "MANUAL_OAE-SIM.pdf"
pdf.output(out)
print("OK ->", out)
