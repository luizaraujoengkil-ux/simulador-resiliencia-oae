"""
Simulador de Resiliência da Rede Viária — Interdição de OAEs

Aplicativo Streamlit para análise de interdição de Obras de Arte Especiais (OAEs)
e impacto na rede viária. Permite carregar uma base de OAEs (CSV/XLSX/KML/KMZ),
visualizar a criticidade em mapa interativo e simular o fechamento de uma ou mais
OAEs, calculando rota original, rota alternativa e indicadores de impacto.

Execução local:
    streamlit run app.py
"""

from __future__ import annotations

import io
import math
import os
import random
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import folium
import networkx as nx
import numpy as np
import pandas as pd
import streamlit as st
from folium.features import DivIcon
from folium.plugins import Fullscreen
from streamlit_folium import st_folium

# ----------------------------------------------------------------------------
# Constantes e configurações
# ----------------------------------------------------------------------------

APP_TITLE = "Simulador de Resiliência da Rede Viária"
APP_SUBTITLE = "Análise de interdição de OAEs críticas e rotas alternativas"
SAMPLE_DATA_PATH = Path(__file__).parent / "sample_data" / "oae_teste.csv"

COLUNA_PADRAO = {
    "codigo": "Código OAE",
    "codigooae": "Código OAE",
    "codigo_oae": "Código OAE",
    "código": "Código OAE",
    "código_oae": "Código OAE",
    "name": "Código OAE",
    "nome": "Código OAE",
    "id": "Código OAE",
    "latitude": "Latitude",
    "lat": "Latitude",
    "y": "Latitude",
    "longitude": "Longitude",
    "lon": "Longitude",
    "lng": "Longitude",
    "long": "Longitude",
    "x": "Longitude",
    "nota": "Nota Geral",
    "notageral": "Nota Geral",
    "nota_geral": "Nota Geral",
    "criticidade": "Nota Geral",
    "score": "Nota Geral",
    "municipio": "Município / UF",
    "município": "Município / UF",
    "municipiouf": "Município / UF",
    "município_uf": "Município / UF",
    "cidade": "Município / UF",
    "rodovia": "Rodovia / Trecho",
    "trecho": "Rodovia / Trecho",
    "rodoviatrecho": "Rodovia / Trecho",
    "rodovia_trecho": "Rodovia / Trecho",
    "tipo": "Tipo",
}

COLUNAS_OBRIGATORIAS = ["Código OAE", "Latitude", "Longitude"]
COLUNAS_OPCIONAIS = ["Nota Geral", "Município / UF", "Rodovia / Trecho", "Tipo"]


# ----------------------------------------------------------------------------
# Estilo (CSS) e cabeçalho
# ----------------------------------------------------------------------------

def aplicar_estilo() -> None:
    """Injeta CSS para deixar o app com visual mais limpo, fluido e compacto."""
    st.markdown(
        """
        <style>
        /* ----- Container principal ----- */
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1500px;
        }

        /* ----- Tipografia geral ----- */
        .stMarkdown h1 { font-size: 1.5rem;  font-weight: 700; margin: 0.5rem 0 0.6rem; color: #F5F8FF; }
        .stMarkdown h2 { font-size: 1.25rem; font-weight: 700; margin: 0.5rem 0 0.5rem; color: #F5F8FF; }
        .stMarkdown h3 { font-size: 1.08rem; font-weight: 600; margin: 0.9rem 0 0.5rem; color: #F5F8FF; }
        .stMarkdown p, .stMarkdown li { font-size: 0.94rem; color: #C8D2E6; }

        /* ----- HERO (gradiente vivo, título escuro) ----- */
        .app-hero {
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg, #1DE9C8 0%, #00CFC8 40%, #00B4D8 70%, #1976D2 100%);
            border: none;
            border-radius: 18px;
            padding: 1.8rem 2rem;
            margin-bottom: 1.4rem;
            display: flex;
            align-items: center;
            gap: 1.4rem;
            color: #0F1B33;
            box-shadow: 0 16px 38px rgba(0, 188, 212, 0.32);
        }
        /* brilho sutil canto superior direito */
        .app-hero::after {
            content: "";
            position: absolute;
            right: -60px; top: -80px;
            width: 280px; height: 280px;
            background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 65%);
            pointer-events: none;
        }
        .app-hero > * { position: relative; z-index: 1; }
        .app-hero .brand {
            display: flex;
            align-items: center;
            gap: 1rem;
            min-width: 0;
            flex: 1;
        }
        .app-hero .hero-icon {
            font-size: 3rem;
            line-height: 1;
            flex-shrink: 0;
            filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.25));
        }
        .app-hero .titlebar { display: flex; flex-direction: column; min-width: 0; }
        .app-hero h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
            color: #0F1B33;
            letter-spacing: -0.02em;
        }
        .app-hero .subtitle {
            margin: 0.55rem 0 0;
            font-size: 1rem;
            color: #163354;
            font-weight: 500;
            opacity: 0.85;
        }
        .app-hero .meta {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            align-items: flex-end;
            flex-shrink: 0;
        }
        .app-hero .pill {
            font-family: 'JetBrains Mono', 'Consolas', 'Cascadia Mono', monospace;
            font-size: 0.7rem;
            background: rgba(15, 27, 51, 0.18);
            border: 1px solid rgba(15, 27, 51, 0.25);
            color: #0F1B33;
            padding: 0.32rem 0.65rem;
            border-radius: 5px;
            letter-spacing: 0.06em;
            font-weight: 700;
            white-space: nowrap;
            backdrop-filter: blur(4px);
        }
        .app-hero .pill.status {
            background: rgba(255, 255, 255, 0.22);
            border-color: rgba(15, 27, 51, 0.2);
            color: #0F2D1F;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }
        .app-hero .pill.status .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #14B86A;
            box-shadow: 0 0 0 3px rgba(20, 184, 106, 0.25);
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 3px rgba(20, 184, 106, 0.25); }
            50%      { box-shadow: 0 0 0 6px rgba(20, 184, 106, 0.0); }
        }

        /* rolagem suave para anchors */
        html { scroll-behavior: smooth; }

        /* ----- STEP CARDS (estilo numerado, título cyan) ----- */
        .card-link {
            text-decoration: none !important;
            color: inherit !important;
            display: block;
            height: 100%;
            cursor: pointer;
        }
        .card-link:hover .step-card {
            border-color: #00E0D4;
            transform: translateY(-2px);
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.4);
        }
        .card-link .step-card::after {
            content: "↓ abrir";
            position: absolute;
            top: 0.6rem; right: 0.8rem;
            font-size: 0.66rem;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            color: #00E0D4;
            opacity: 0.55;
            letter-spacing: 0.06em;
        }
        .card-link:hover .step-card::after { opacity: 1; }
        .step-card {
            position: relative;
            background: #0F1B33;
            border: 1px solid #1F2D4A;
            border-radius: 12px;
            padding: 1.1rem 1.2rem 1.15rem;
            height: 100%;
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        }
        .step-card:hover {
            transform: translateY(-2px);
            border-color: #00E0D4;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.4);
        }
        .step-card .title {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            margin: 0 0 0.55rem;
            font-size: 1.08rem;
            font-weight: 700;
            color: #00E0D4;
            line-height: 1.25;
        }
        .step-card .title .emoji {
            font-size: 1.25rem;
            line-height: 1;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
        }
        .step-card p {
            margin: 0;
            font-size: 0.92rem;
            color: #C8D2E6;
            line-height: 1.5;
        }

        /* ----- Métricas ----- */
        .metric-card {
            background: #101B2E;
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
            border-left: 3px solid #00E0D4;
        }
        .metric-card .label {
            font-size: 0.68rem;
            color: #A8B3C7;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-card .value {
            font-size: 1.2rem;
            font-weight: 700;
            color: #FFFFFF;
            margin-top: 0.15rem;
        }
        .status-ok { color: #16C172; font-weight: 700; }
        .status-warn { color: #F4A261; font-weight: 700; }
        .status-fail { color: #E63946; font-weight: 700; }

        /* ----- Botões ----- */
        .stButton > button {
            background: linear-gradient(90deg, #00E0D4, #1E6091);
            color: #07111F;
            font-weight: 700;
            border-radius: 8px;
            border: none;
            padding: 0.45rem 1rem;
            font-size: 0.88rem;
        }
        .stButton > button:hover {
            filter: brightness(1.08);
            color: #07111F;
        }

        /* ----- Sidebar ----- */
        section[data-testid="stSidebar"] {
            min-width: 340px !important;
            width: 340px !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem !important;
            padding-left: 1.1rem !important;
            padding-right: 1.1rem !important;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2 { font-size: 1.05rem; margin-bottom: 0.5rem; }
        section[data-testid="stSidebar"] h3 { font-size: 0.92rem; margin: 0.75rem 0 0.3rem; color: #C8D2E6; }
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] label { font-size: 0.86rem; }
        /* uploader hint nao trunca */
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small {
            white-space: normal !important;
        }

        /* ----- Espaçamento entre blocos um pouco menor ----- */
        [data-testid="stVerticalBlock"] { gap: 0.5rem; }

        /* ----- Notas auxiliares ----- */
        .small-note {
            font-size: 0.82rem;
            opacity: 0.8;
        }
        .data-format-hint {
            margin: 0.4rem 0 0.2rem;
            padding: 0.6rem 0.75rem;
            background: rgba(0, 224, 212, 0.06);
            border: 1px solid rgba(0, 224, 212, 0.25);
            border-left: 2px solid #00E0D4;
            border-radius: 6px;
            font-size: 0.78rem;
            color: #C8D2E6;
            line-height: 1.4;
        }
        .data-format-hint .hint-title {
            color: #00E0D4;
            font-weight: 700;
            margin-bottom: 0.35rem;
            font-size: 0.78rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .data-format-hint .row { margin-top: 0.2rem; }
        .data-format-hint b { color: #F5F8FF; }
        .data-format-hint code {
            background: rgba(255, 255, 255, 0.06);
            color: #C8D2E6;
            padding: 0.05rem 0.3rem;
            border-radius: 3px;
            font-size: 0.74rem;
        }
        .slider-hint {
            margin: -0.2rem 0 0.4rem;
            padding: 0.45rem 0.6rem;
            background: rgba(244, 162, 97, 0.08);
            border-left: 2px solid #F4A261;
            border-radius: 4px;
            font-size: 0.76rem;
            color: #C8D2E6;
            line-height: 1.4;
        }
        .slider-hint b { color: #F4A261; }
        .slider-hint code {
            background: rgba(255, 255, 255, 0.06);
            color: #F5F8FF;
            padding: 0.05rem 0.28rem;
            border-radius: 3px;
            font-size: 0.72rem;
        }
        .selection-counter {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0.3rem 0 0.5rem;
            padding: 0.5rem 0.7rem;
            background: rgba(230, 57, 70, 0.07);
            border-left: 2px solid #E63946;
            border-radius: 4px;
            font-size: 0.8rem;
            color: #C8D2E6;
        }
        .selection-counter .count {
            color: #FFFFFF;
            font-weight: 700;
        }
        .selection-counter .total {
            font-size: 0.74rem;
            color: #8FA0BA;
        }
        .selection-counter.empty {
            background: rgba(143, 160, 186, 0.06);
            border-left-color: #8FA0BA;
        }
        .filter-hint {
            margin: -0.3rem 0 0.4rem;
            padding: 0.4rem 0.6rem;
            background: rgba(0, 224, 212, 0.06);
            border-left: 2px solid #00E0D4;
            border-radius: 4px;
            font-size: 0.76rem;
            color: #C8D2E6;
        }
        .filter-hint b { color: #F5F8FF; }
        .sim-counter {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0.4rem 0 0.3rem;
            padding: 0.55rem 0.75rem;
            background: linear-gradient(90deg, rgba(0, 224, 212, 0.08), rgba(111, 168, 255, 0.05));
            border: 1px solid rgba(0, 224, 212, 0.3);
            border-radius: 6px;
            font-size: 0.82rem;
            color: #C8D2E6;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
        }
        .sim-counter .count {
            color: #00E0D4;
            font-weight: 700;
            font-size: 1.1rem;
        }
        /* Legenda em destaque acima do mapa quando há interdições */
        .legenda-destaque {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.7rem;
            padding: 0.7rem 1rem;
            margin: 0.4rem 0 0.7rem;
            background: linear-gradient(90deg, rgba(230, 57, 70, 0.12), rgba(230, 57, 70, 0.04));
            border: 1px solid rgba(230, 57, 70, 0.3);
            border-left: 4px solid #E63946;
            border-radius: 8px;
            font-size: 0.88rem;
            color: #F5F8FF;
        }
        .legenda-destaque .badge {
            background: #E63946;
            color: #FFFFFF;
            font-weight: 800;
            padding: 0.15rem 0.55rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }
        .legenda-destaque .legend-pill {
            background: rgba(255, 255, 255, 0.06);
            padding: 0.18rem 0.5rem;
            border-radius: 4px;
            font-size: 0.78rem;
            color: #C8D2E6;
        }
        /* Banner do cenário de interdição */
        .interdicao-banner {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            padding: 1rem 1.25rem;
            margin: 0.5rem 0 1rem;
            background: linear-gradient(135deg, rgba(230, 57, 70, 0.18), rgba(244, 162, 97, 0.08));
            border: 1px solid rgba(230, 57, 70, 0.4);
            border-left: 4px solid #E63946;
            border-radius: 10px;
        }
        .interdicao-banner .emoji {
            font-size: 1.7rem;
            line-height: 1;
        }
        .interdicao-banner .count {
            font-size: 2rem;
            font-weight: 800;
            color: #FFFFFF;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1;
        }
        .interdicao-banner .label {
            font-size: 1.05rem;
            color: #F5F8FF;
            font-weight: 600;
        }
        .interdicao-banner .total {
            margin-left: auto;
            font-size: 0.82rem;
            color: #A8B5CC;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 0.04em;
        }
        /* Estado vazio */
        .empty-state {
            text-align: center;
            padding: 2rem 1.5rem;
            background: #0F1B33;
            border: 1px dashed #2A3B5C;
            border-radius: 12px;
            margin: 0.5rem 0 1rem;
        }
        .empty-state .big-emoji {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            opacity: 0.8;
        }
        .empty-state .big-text {
            font-size: 1.05rem;
            font-weight: 600;
            color: #F5F8FF;
            margin-bottom: 0.4rem;
        }
        .empty-state .small-text {
            font-size: 0.9rem;
            color: #A8B5CC;
        }
        .empty-state b { color: #00E0D4; }
        </style>
        """,
        unsafe_allow_html=True,
    )


APP_VERSAO = "v0.1"
APP_MODULO = "OAE-SIM"


def cabecalho() -> None:
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="brand">
                <span class="hero-icon">🌉</span>
                <div class="titlebar">
                    <h1>{APP_TITLE}</h1>
                    <span class="subtitle">{APP_SUBTITLE}</span>
                </div>
            </div>
            <div class="meta">
                <span class="pill">{APP_MODULO} · {APP_VERSAO}</span>
                <span class="pill status"><span class="dot"></span>ATIVO</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


ICONE_PASTA = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    '</svg>'
)
ICONE_MAPA = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/>'
    '<path d="M9 4v14"/><path d="M15 6v14"/>'
    '</svg>'
)
ICONE_INTERDICAO = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"/>'
    '<path d="M5.6 5.6l12.8 12.8"/>'
    '</svg>'
)
ICONE_IMPACTO = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M4 19V5"/><path d="M4 19h16"/>'
    '<path d="M7 16v-4"/><path d="M12 16V8"/><path d="M17 16v-6"/>'
    '</svg>'
)


def cards_explicativos() -> None:
    etapas = [
        ("1", "📁", "Carregar base",
         "Importe CSV, XLSX, KML ou KMZ com as OAEs.",
         "planilha-dados"),
        ("2", "🗺️", "Visualizar mapa",
         "Veja a criticidade no mapa interativo (botão ⛶ abre em tela cheia).",
         "mapa-criticidade"),
        ("3", "⛔", "Selecionar interdição",
         "Veja quais OAEs estão fechadas no cenário atual.",
         "cenario-interdicao"),
        ("4", "📊", "Calcular impacto",
         "Compare rotas, indicadores e baixe o relatório em PDF.",
         "relatorio"),
    ]
    cols = st.columns(len(etapas), gap="small")
    for col, (num, emoji, titulo, texto, anchor) in zip(cols, etapas):
        card_html = f"""
            <div class="step-card">
                <div class="title">
                    <span class="emoji">{emoji}</span>
                    <span>{num}. {titulo}</span>
                </div>
                <p>{texto}</p>
            </div>
        """
        if anchor:
            html = f'<a href="#{anchor}" class="card-link">{card_html}</a>'
        else:
            html = card_html
        col.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Padronização e carregamento de dados
# ----------------------------------------------------------------------------

def _normaliza_chave(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace(" ", "").replace("/", "").replace("-", "").replace(".", "")
    s = s.replace("__", "_")
    return s


def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas conforme dicionário e converte tipos básicos."""
    novo_nome = {}
    for col in df.columns:
        chave = _normaliza_chave(col)
        if chave in COLUNA_PADRAO:
            novo_nome[col] = COLUNA_PADRAO[chave]
    df = df.rename(columns=novo_nome)

    # Conversão numérica
    for c in ("Latitude", "Longitude", "Nota Geral"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Remove linhas sem coordenadas
    if "Latitude" in df.columns and "Longitude" in df.columns:
        df = df.dropna(subset=["Latitude", "Longitude"]).copy()
    else:
        return pd.DataFrame()

    # Cria Código OAE se faltar
    if "Código OAE" not in df.columns:
        df["Código OAE"] = [f"OAE-{i+1:03d}" for i in range(len(df))]
    else:
        df["Código OAE"] = df["Código OAE"].astype(str).str.strip()
        df.loc[df["Código OAE"].isin(["", "nan", "None"]), "Código OAE"] = [
            f"OAE-{i+1:03d}" for i in range((df["Código OAE"].isin(["", "nan", "None"])).sum())
        ]

    # Preenche opcionais
    if "Nota Geral" not in df.columns:
        df["Nota Geral"] = 3.0
    df["Nota Geral"] = df["Nota Geral"].fillna(3.0)

    if "Município / UF" not in df.columns:
        df["Município / UF"] = "Não informado"
    df["Município / UF"] = df["Município / UF"].fillna("Não informado").astype(str)

    if "Rodovia / Trecho" not in df.columns:
        df["Rodovia / Trecho"] = "Não informado"
    df["Rodovia / Trecho"] = df["Rodovia / Trecho"].fillna("Não informado").astype(str)

    if "Tipo" not in df.columns:
        df["Tipo"] = "OAE"
    df["Tipo"] = df["Tipo"].fillna("OAE").astype(str)

    # Deduplica códigos
    if df["Código OAE"].duplicated().any():
        df["Código OAE"] = df["Código OAE"] + "_" + df.groupby("Código OAE").cumcount().astype(str)
        df["Código OAE"] = df["Código OAE"].str.replace(r"_0$", "", regex=True)

    return df.reset_index(drop=True)


def _ler_csv(buf: bytes) -> pd.DataFrame:
    """Lê CSV detectando separador (vírgula ou ponto-e-vírgula)."""
    texto = buf.decode("utf-8-sig", errors="replace")
    for sep in (None, ";", ",", "\t"):
        try:
            df = pd.read_csv(io.StringIO(texto), sep=sep, engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue
    return pd.read_csv(io.StringIO(texto))


def _ler_xlsx(buf: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(buf))


# Cores de referência (RGB) usadas no Google Earth para criticidade — mapeadas para Nota Geral
_CORES_REFERENCIA_NOTA = {
    1: (255,   0,   0),  # vermelho puro
    2: (255,  85, 127),  # rosa
    3: (255, 170,   0),  # laranja
    4: (255, 255, 127),  # amarelo claro
    5: ( 85, 255, 127),  # verde claro
}


def _kml_color_para_rgb(kml_color: str) -> tuple[int, int, int] | None:
    """Converte cor KML (AABBGGRR, 8 hex chars) em tupla RGB."""
    c = (kml_color or "").strip().lower()
    if len(c) != 8:
        return None
    try:
        b = int(c[2:4], 16)
        g = int(c[4:6], 16)
        r = int(c[6:8], 16)
        return (r, g, b)
    except ValueError:
        return None


def _rgb_para_nota(rgb: tuple[int, int, int] | None) -> float | None:
    """Mapeia RGB para Nota Geral (1-5) pela cor de referência mais próxima."""
    if rgb is None:
        return None
    melhor_nota = None
    melhor_dist = float("inf")
    for nota, ref in _CORES_REFERENCIA_NOTA.items():
        d = sum((a - b) ** 2 for a, b in zip(rgb, ref))
        if d < melhor_dist:
            melhor_dist = d
            melhor_nota = nota
    return float(melhor_nota) if melhor_nota is not None else None


def _parse_kml_bytes(kml_bytes: bytes) -> pd.DataFrame:
    """Faz parse de KML puro extraindo Placemarks com Point coordinates.

    Também extrai a cor do IconStyle de cada Placemark (resolvendo StyleMap)
    e mapeia para Nota Geral conforme as cores-padrão usadas no Google Earth.
    """
    try:
        texto = kml_bytes.decode("utf-8", errors="replace")
    except Exception:
        texto = kml_bytes.decode("latin-1", errors="replace")

    # Remove namespaces para simplificar XPath
    try:
        root = ET.fromstring(texto)
    except ET.ParseError:
        idx = texto.find("<kml")
        if idx > 0:
            texto = texto[idx:]
        root = ET.fromstring(texto)

    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    # ----- 1) Mapa de Style.id -> cor RGB (extraída do IconStyle/color) -----
    style_cores: dict[str, tuple[int, int, int]] = {}
    for style in root.iter("Style"):
        style_id = style.attrib.get("id", "")
        if not style_id:
            continue
        icon_style = style.find("IconStyle")
        if icon_style is None:
            continue
        color_el = icon_style.find("color")
        if color_el is None or not color_el.text:
            continue
        rgb = _kml_color_para_rgb(color_el.text)
        if rgb:
            style_cores[style_id] = rgb

    # ----- 2) Mapa de StyleMap.id -> Style.id (chave "normal") -----
    stylemap_to_style: dict[str, str] = {}
    for sm in root.iter("StyleMap"):
        sm_id = sm.attrib.get("id", "")
        if not sm_id:
            continue
        for pair in sm.iter("Pair"):
            key_el = pair.find("key")
            url_el = pair.find("styleUrl")
            if (
                key_el is not None and (key_el.text or "").strip() == "normal"
                and url_el is not None and (url_el.text or "").strip()
            ):
                ref = url_el.text.strip().lstrip("#")
                stylemap_to_style[sm_id] = ref
                break

    def _resolve_cor(style_url_raw: str) -> tuple[int, int, int] | None:
        ref = (style_url_raw or "").strip().lstrip("#")
        if not ref:
            return None
        if ref in style_cores:
            return style_cores[ref]
        if ref in stylemap_to_style:
            return style_cores.get(stylemap_to_style[ref])
        return None

    # ----- 3) Placemarks -----
    registros = []
    for pm in root.iter("Placemark"):
        nome_el = pm.find("name")
        nome = nome_el.text.strip() if nome_el is not None and nome_el.text else None
        desc_el = pm.find("description")
        descricao = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        # ExtendedData
        extras: dict[str, str] = {}
        for data in pm.iter("Data"):
            nome_attr = data.attrib.get("name", "")
            valor_el = data.find("value")
            if nome_attr and valor_el is not None and valor_el.text:
                extras[nome_attr.strip()] = valor_el.text.strip()
        for sd in pm.iter("SimpleData"):
            nome_attr = sd.attrib.get("name", "")
            if nome_attr and sd.text:
                extras[nome_attr.strip()] = sd.text.strip()

        # Cor: a) styleUrl referenciado; b) IconStyle inline
        rgb = None
        style_url_el = pm.find("styleUrl")
        if style_url_el is not None and style_url_el.text:
            rgb = _resolve_cor(style_url_el.text)
        if rgb is None:
            for inline in pm.iter("IconStyle"):
                color_el = inline.find("color")
                if color_el is not None and color_el.text:
                    rgb = _kml_color_para_rgb(color_el.text)
                    if rgb:
                        break

        nota_da_cor = _rgb_para_nota(rgb)

        for ponto in pm.iter("Point"):
            coords_el = ponto.find("coordinates")
            if coords_el is None or not coords_el.text:
                continue
            for raw in coords_el.text.strip().split():
                partes = raw.strip().split(",")
                if len(partes) < 2:
                    continue
                try:
                    lon = float(partes[0])
                    lat = float(partes[1])
                except ValueError:
                    continue
                registro = {
                    "Código OAE": nome or "",
                    "Latitude": lat,
                    "Longitude": lon,
                    "Descrição": descricao,
                }
                if nota_da_cor is not None:
                    registro["Nota Geral"] = nota_da_cor
                registro.update(extras)
                registros.append(registro)

    if not registros:
        return pd.DataFrame()
    return pd.DataFrame(registros)


def _ler_kmz(buf: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(buf)) as zf:
        nomes_kml = [n for n in zf.namelist() if n.lower().endswith(".kml")]
        if not nomes_kml:
            return pd.DataFrame()
        # prioriza doc.kml se existir
        nomes_kml.sort(key=lambda n: (0 if n.lower().endswith("doc.kml") else 1, n))
        with zf.open(nomes_kml[0]) as f:
            return _parse_kml_bytes(f.read())


def carregar_arquivo(arquivo) -> pd.DataFrame:
    """Carrega DataFrame a partir de um UploadedFile do Streamlit ou Path."""
    if arquivo is None:
        return pd.DataFrame()

    # Path local (ex.: base de demonstração)
    if isinstance(arquivo, (str, os.PathLike)):
        p = Path(arquivo)
        nome = p.name.lower()
        dados = p.read_bytes()
    else:
        nome = getattr(arquivo, "name", "upload").lower()
        dados = arquivo.read()

    try:
        if nome.endswith(".csv") or nome.endswith(".txt"):
            df = _ler_csv(dados)
        elif nome.endswith(".xlsx") or nome.endswith(".xls"):
            df = _ler_xlsx(dados)
        elif nome.endswith(".kmz"):
            df = _ler_kmz(dados)
        elif nome.endswith(".kml"):
            df = _parse_kml_bytes(dados)
        else:
            # fallback: tenta CSV
            df = _ler_csv(dados)
    except Exception as exc:
        st.error(f"Falha ao ler o arquivo: {exc}")
        return pd.DataFrame()

    if df is None or df.empty:
        st.warning("Nenhum registro pôde ser extraído do arquivo.")
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    df = padronizar_colunas(df)
    if df.empty:
        st.warning("O arquivo não contém colunas de Latitude/Longitude reconhecíveis.")
    return df


# ----------------------------------------------------------------------------
# Cores e mapa
# ----------------------------------------------------------------------------

def cor_criticidade(nota) -> str:
    if nota is None or (isinstance(nota, float) and math.isnan(nota)):
        return "#9AA0A6"
    try:
        n = float(nota)
    except Exception:
        return "#9AA0A6"
    if n <= 1.5:
        return "#8B0000"      # vermelho escuro
    if n <= 2.5:
        return "#E63946"      # vermelho
    if n <= 3.5:
        return "#F4A261"      # laranja
    if n <= 4.5:
        return "#F1C40F"      # amarelo
    return "#2ECC71"           # verde


def desenhar_mapa(
    df: pd.DataFrame,
    rotas: list[dict] | None = None,
    interditadas: Iterable[str] | None = None,
    malha: dict | None = None,
    titulo: str | None = None,
) -> folium.Map:
    """Cria um folium.Map com as OAEs, malha viária (opcional) e rotas (opcional).

    rotas: lista de {"coords": [(lat,lon),...], "color": str, "label": str, "weight": int, "dash_array": str}.
    malha: GeoJSON FeatureCollection com a malha viária (LineStrings em [lon,lat]).
    """
    if df.empty:
        return folium.Map(location=[-15.78, -47.93], zoom_start=4, control_scale=True)

    centro_lat = float(df["Latitude"].mean())
    centro_lon = float(df["Longitude"].mean())
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=11, control_scale=True, tiles="cartodbpositron")

    # Botão de tela cheia (canto superior direito)
    Fullscreen(
        position="topright",
        title="Expandir para tela cheia",
        title_cancel="Sair da tela cheia",
        force_separate_button=True,
    ).add_to(m)

    # Malha viária (fundo azul) — renderizada PRIMEIRO para ficar atrás de tudo
    if malha and malha.get("features"):
        folium.GeoJson(
            malha,
            name="Malha viária",
            style_function=lambda x: {
                "color": "#1976D2",
                "weight": 2.0,
                "opacity": 0.65,
            },
        ).add_to(m)

    if titulo:
        folium.map.Marker(
            [centro_lat, centro_lon],
            icon=DivIcon(
                icon_size=(300, 36),
                icon_anchor=(0, 0),
                html=f'<div style="font-size:14pt; font-weight:700; color:#0B2545; '
                     f'background:rgba(255,255,255,0.85); padding:4px 10px; border-radius:6px;">{titulo}</div>',
            ),
        ).add_to(m)

    interditadas = set(map(str, interditadas or []))

    for _, row in df.iterrows():
        codigo = str(row["Código OAE"])
        nota = row.get("Nota Geral", None)
        cor = cor_criticidade(nota)
        interditada = codigo in interditadas

        popup_html = (
            f"<b>Código:</b> {codigo}<br>"
            f"<b>Nota Geral:</b> {nota}<br>"
            f"<b>Município/UF:</b> {row.get('Município / UF', '-')}<br>"
            f"<b>Rodovia/Trecho:</b> {row.get('Rodovia / Trecho', '-')}<br>"
            f"<b>Lat:</b> {row['Latitude']:.5f} &nbsp; <b>Lon:</b> {row['Longitude']:.5f}"
        )

        if interditada:
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"⛔ {codigo} (interditada)",
                icon=folium.Icon(color="black", icon="ban", prefix="fa"),
            ).add_to(m)
        else:
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=7,
                color=cor,
                weight=2,
                fill=True,
                fill_color=cor,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"{codigo} — Nota {nota}",
            ).add_to(m)

    if rotas:
        for rota in rotas:
            coords = rota.get("coords") or []
            if len(coords) < 2:
                continue
            pl_kwargs = dict(
                color=rota.get("color", "#1E6091"),
                weight=rota.get("weight", 5),
                opacity=rota.get("opacity", 0.9),
                tooltip=rota.get("label", "Rota"),
            )
            if rota.get("dash_array"):
                pl_kwargs["dash_array"] = rota["dash_array"]
            folium.PolyLine(coords, **pl_kwargs).add_to(m)

    # Legenda — inclui malha e rotas se houver
    blocos_extra = ""
    if malha and malha.get("features"):
        blocos_extra += '<hr style="margin:6px 0;border:none;border-top:1px solid #DDD;">'
        blocos_extra += '<b>Rede / rotas</b><br>'
        blocos_extra += '<span style="color:#1E88E5;">━</span> Malha viária<br>'
    if rotas:
        if not blocos_extra:
            blocos_extra += '<hr style="margin:6px 0;border:none;border-top:1px solid #DDD;">'
            blocos_extra += '<b>Rotas</b><br>'
        for rota in rotas:
            cor = rota.get("color", "#1E6091")
            label = rota.get("label", "Rota")
            stroke = "┄ ┄" if rota.get("dash_array") else "━"
            blocos_extra += f'<span style="color:{cor};">{stroke}</span> {label}<br>'

    legenda = f"""
    <div style="position: fixed; bottom: 30px; left: 30px; z-index:9999;
                background:#FFFFFF; padding:8px 12px; border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,0.25); color:#0B2545; font-size:12px;
                max-width: 230px;">
      <b>Criticidade (Nota Geral)</b><br>
      <span style="color:#8B0000;">●</span> 1 — Crítica<br>
      <span style="color:#E63946;">●</span> 2 — Ruim<br>
      <span style="color:#F4A261;">●</span> 3 — Regular<br>
      <span style="color:#F1C40F;">●</span> 4 — Boa<br>
      <span style="color:#2ECC71;">●</span> 5 — Ótima<br>
      <span style="color:#9AA0A6;">●</span> Sem nota<br>
      ⛔ Interditada
      {blocos_extra}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legenda))
    return m


def _area_de_interesse(
    df: pd.DataFrame,
    interdicao: list[str],
    origem: str | None,
    destino: str | None,
    buffer_km: float = 2.0,
) -> tuple[float, float, float] | None:
    """Calcula (centro_lat, centro_lon, raio_m) cobrindo as OAEs envolvidas no cenário.

    Junta as coordenadas das OAEs interditadas + origem + destino, calcula o centroide
    e o raio mínimo que cobre todos esses pontos. Adiciona o buffer (em km) como margem.
    Retorna None se não houver OAEs envolvidas.
    """
    codigos: list[str] = []
    if interdicao:
        codigos.extend(str(c) for c in interdicao)
    if origem:
        codigos.append(str(origem))
    if destino:
        codigos.append(str(destino))
    if not codigos:
        return None

    pontos: list[tuple[float, float]] = []
    vistos: set[str] = set()
    for cod in codigos:
        if cod in vistos:
            continue
        vistos.add(cod)
        sel = df[df["Código OAE"].astype(str) == cod]
        if sel.empty:
            continue
        linha = sel.iloc[0]
        try:
            pontos.append((float(linha["Latitude"]), float(linha["Longitude"])))
        except (TypeError, ValueError):
            continue

    if not pontos:
        return None

    centro_lat = sum(p[0] for p in pontos) / len(pontos)
    centro_lon = sum(p[1] for p in pontos) / len(pontos)

    if len(pontos) == 1:
        # Único ponto: raio = só o buffer (com mínimo de 1.5 km)
        raio_m = max(buffer_km * 1000.0, 1500.0)
    else:
        max_dist_m = max(_haversine_m(centro_lat, centro_lon, p[0], p[1]) for p in pontos)
        raio_m = max_dist_m + buffer_km * 1000.0
        raio_m = max(raio_m, 1500.0)

    return centro_lat, centro_lon, raio_m


def _extrair_malha_geojson(G) -> dict:
    """Extrai todas as arestas do grafo OSM como FeatureCollection GeoJSON."""
    features = []
    for u, v, data in G.edges(data=True):
        geom = data.get("geometry")
        if geom is not None:
            try:
                # shapely LineString: coords são (x, y) = (lon, lat) — formato GeoJSON
                coords = [list(c) for c in geom.coords]
            except Exception:
                continue
        else:
            try:
                coords = [
                    [G.nodes[u]["x"], G.nodes[u]["y"]],
                    [G.nodes[v]["x"], G.nodes[v]["y"]],
                ]
            except KeyError:
                continue
        if len(coords) >= 2:
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {},
            })
    return {"type": "FeatureCollection", "features": features}


# ----------------------------------------------------------------------------
# Cálculo de rotas — Modo A (OSMnx) e Modo B (simplificado)
# ----------------------------------------------------------------------------

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@st.cache_resource(show_spinner=False)
def construir_grafo_osm(centro_lat: float, centro_lon: float, raio_m: int) -> "nx.MultiDiGraph | None":
    """Baixa rede viária via OSMnx. Retorna None se falhar (sem internet etc.)."""
    try:
        import osmnx as ox  # import tardio para que app suba mesmo sem osmnx funcional
    except Exception:
        return None
    try:
        G = ox.graph_from_point((centro_lat, centro_lon), dist=raio_m, network_type="drive")
        # osmnx 2.x: add_edge_lengths foi movido para o submódulo distance
        add_lengths = getattr(ox.distance, "add_edge_lengths", None) or getattr(ox, "add_edge_lengths", None)
        if add_lengths is not None:
            G = add_lengths(G)
        return G
    except Exception:
        return None


def _no_mais_proximo(G: nx.MultiDiGraph, lat: float, lon: float) -> int | None:
    try:
        import osmnx as ox
        return int(ox.distance.nearest_nodes(G, lon, lat))
    except Exception:
        # fallback manual
        melhor, melhor_d = None, float("inf")
        for n, data in G.nodes(data=True):
            d = _haversine_m(lat, lon, data["y"], data["x"])
            if d < melhor_d:
                melhor_d, melhor = d, n
        return melhor


def calcular_rota_osm(
    G: nx.MultiDiGraph,
    origem: tuple[float, float],
    destino: tuple[float, float],
    nos_remover: set[int] | None = None,
) -> tuple[list[tuple[float, float]], float]:
    """Calcula caminho mais curto. Retorna (coords [(lat,lon)...], distancia_m)."""
    H = G
    if nos_remover:
        H = G.copy()
        H.remove_nodes_from([n for n in nos_remover if n in H.nodes])

    o = _no_mais_proximo(H, *origem)
    d = _no_mais_proximo(H, *destino)
    if o is None or d is None:
        return [], 0.0
    try:
        caminho = nx.shortest_path(H, o, d, weight="length")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], 0.0
    coords = [(H.nodes[n]["y"], H.nodes[n]["x"]) for n in caminho]
    dist = 0.0
    for u, v in zip(caminho[:-1], caminho[1:]):
        edata = H.get_edge_data(u, v)
        if edata:
            dist += min(d.get("length", 0.0) for d in edata.values())
    return coords, dist


def construir_grafo_simplificado(df: pd.DataFrame, k_vizinhos: int = 3) -> nx.Graph:
    """Cria grafo conectando cada OAE aos k vizinhos mais próximos (rede simplificada)."""
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_node(str(row["Código OAE"]), y=float(row["Latitude"]), x=float(row["Longitude"]))

    nos = list(G.nodes(data=True))
    for i, (ni, di) in enumerate(nos):
        dists = []
        for j, (nj, dj) in enumerate(nos):
            if i == j:
                continue
            d = _haversine_m(di["y"], di["x"], dj["y"], dj["x"])
            dists.append((d, nj))
        dists.sort()
        for d, nj in dists[:k_vizinhos]:
            if not G.has_edge(ni, nj):
                G.add_edge(ni, nj, length=d)
    return G


def calcular_rota_simplificada(
    G: nx.Graph,
    origem_codigo: str,
    destino_codigo: str,
    nos_remover: set[str] | None = None,
) -> tuple[list[tuple[float, float]], float]:
    H = G
    if nos_remover:
        H = G.copy()
        H.remove_nodes_from([n for n in nos_remover if n in H.nodes])
    if origem_codigo not in H.nodes or destino_codigo not in H.nodes:
        return [], 0.0
    try:
        caminho = nx.shortest_path(H, origem_codigo, destino_codigo, weight="length")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], 0.0
    coords = [(H.nodes[n]["y"], H.nodes[n]["x"]) for n in caminho]
    dist = sum(H[u][v]["length"] for u, v in zip(caminho[:-1], caminho[1:]))
    return coords, dist


# ----------------------------------------------------------------------------
# Indicadores
# ----------------------------------------------------------------------------

def _fmt_km(metros: float) -> str:
    if metros is None or metros <= 0:
        return "—"
    return f"{metros / 1000:.2f} km"


def cards_indicadores(
    total: int,
    interditadas: int,
    dist_orig_m: float,
    dist_alt_m: float,
    tem_alt: bool,
) -> None:
    delta_m = (dist_alt_m - dist_orig_m) if (dist_orig_m and dist_alt_m) else 0.0
    pct = (delta_m / dist_orig_m * 100) if dist_orig_m else 0.0

    if not tem_alt:
        status_html = '<span class="status-fail">Sem rota alternativa detectada</span>'
    elif delta_m > 0:
        status_html = '<span class="status-warn">Rota alternativa com aumento</span>'
    else:
        status_html = '<span class="status-ok">Rota alternativa encontrada</span>'

    indicadores = [
        ("Total de OAEs", str(total)),
        ("OAEs interditadas", str(interditadas)),
        ("Distância original", _fmt_km(dist_orig_m)),
        ("Distância alternativa", _fmt_km(dist_alt_m) if tem_alt else "—"),
        ("Aumento", _fmt_km(delta_m) if tem_alt else "—"),
        ("Variação %", f"{pct:+.1f}%" if tem_alt and dist_orig_m else "—"),
    ]

    cols = st.columns(len(indicadores))
    for col, (label, valor) in zip(cols, indicadores):
        col.markdown(
            f'<div class="metric-card"><div class="label">{label}</div>'
            f'<div class="value">{valor}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(f"**Status da rede:** {status_html}", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# UI principal
# ----------------------------------------------------------------------------

def sidebar_inputs(df: pd.DataFrame) -> dict:
    """Renderiza a sidebar e devolve as escolhas do usuário."""
    st.sidebar.header("⚙️ Controles")

    usar_demo = st.sidebar.toggle("Usar base de demonstração", value=True, help="Carrega sample_data/oae_teste.csv")
    arquivo = st.sidebar.file_uploader(
        "Carregar arquivo(s)",
        type=["csv", "xlsx", "xls", "kml", "kmz"],
        help="Formatos: CSV, XLSX, KML, KMZ. Pode selecionar vários arquivos ao mesmo tempo "
             "— eles são consolidados em uma única base. KMZs com cor de ícone são "
             "convertidos para Nota Geral 1-5 automaticamente.",
        accept_multiple_files=True,
    )
    st.sidebar.markdown(
        """
        <div class="data-format-hint">
            <div class="hint-title">ℹ️ Formato esperado</div>
            <div class="row"><b>Obrigatórias:</b> <code>Latitude</code>, <code>Longitude</code></div>
            <div class="row"><b>Opcionais (recomendadas):</b> <code>Código OAE</code>, <code>Nota Geral</code>, <code>Município</code>, <code>Rodovia</code>, <code>Tipo</code></div>
            <div class="row">Aceita variações: <code>lat</code>, <code>lng</code>, <code>nota</code>, <code>cidade</code>, <code>trecho</code>...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Rede viária")
    modo_rede = st.sidebar.radio(
        "Modo de cálculo",
        ["Automático (OSM → simplificado se falhar)", "Forçar modo simplificado"],
        index=0,
    )
    buffer_km = st.sidebar.slider(
        "Buffer (km) ao redor da área de interesse",
        1, 10, value=2,
        help="No mapa geral o raio é calculado a partir do centroide das OAEs interditadas. "
             "Na simulação inclui também origem + destino. Este buffer adiciona contexto "
             "ao redor (recomendado: 2-5 km).",
    )
    st.sidebar.markdown(
        """
        <div class="slider-hint">
            ℹ️ <b>Raio automático:</b><br>
            • <b>Mapa geral:</b> centroide das OAEs interditadas + buffer<br>
            • <b>Simulação:</b> interditadas + origem/destino + buffer
        </div>
        """,
        unsafe_allow_html=True,
    )

    mostrar_malha = st.sidebar.toggle(
        "🌐 Mostrar malha viária no mapa geral",
        value=False,
        help="Baixa a rede viária do OSM centrada nas OAEs interditadas e desenha "
             "por cima do mapa de criticidade. Só funciona após selecionar interdição. "
             "A 1ª ativação demora alguns segundos (depois fica em cache).",
    )

    interdicao: list[str] = []
    origem = destino = None
    executar = False
    if not df.empty:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Interdição")
        opcoes = df["Código OAE"].astype(str).tolist()
        tem_nota = "Nota Geral" in df.columns

        # ---- Quantidade de OAEs a marcar como críticas ----
        max_crit = min(10, len(opcoes))
        qtd_criticas = st.sidebar.number_input(
            "Quantas OAEs marcar como críticas?",
            min_value=1,
            max_value=max(1, max_crit),
            value=1,
            step=1,
            help="O botão abaixo seleciona automaticamente as N piores OAEs por Nota Geral "
                 "(1 = crítica → 5 = ótima). Limite: 10 OAEs.",
            key="qtd_criticas",
        )

        # Lista das N piores (Nota Geral ascendente). Se não houver nota, usa ordem original.
        if tem_nota:
            piores = (
                df.sort_values("Nota Geral", ascending=True, kind="stable")
                  ["Código OAE"].astype(str).tolist()
            )
        else:
            piores = opcoes[:]
        selecao_criticas = piores[: int(qtd_criticas)]

        # Preview da seleção que será aplicada
        if selecao_criticas:
            preview = " · ".join(
                f"{cod} (Nota {df.loc[df['Código OAE'].astype(str)==cod, 'Nota Geral'].iloc[0]:.0f})"
                if tem_nota else cod
                for cod in selecao_criticas[:5]
            )
            if len(selecao_criticas) > 5:
                preview += f" … +{len(selecao_criticas) - 5}"
            st.sidebar.markdown(
                f"""
                <div class="filter-hint">
                    📋 <b>Pré-seleção:</b> {preview}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---- Botões de ação ----
        col_a, col_b = st.sidebar.columns(2)
        sel_atual = st.session_state.get("interdicao_select", [])
        if col_a.button(
            f"📌 Aplicar ({len(selecao_criticas)})",
            use_container_width=True,
            disabled=len(selecao_criticas) == 0,
            help="Marca como interditadas as N piores OAEs selecionadas acima.",
            key="btn_aplicar_filtro",
        ):
            st.session_state["interdicao_select"] = selecao_criticas
            st.rerun()
        if col_b.button(
            "🗑️ Limpar",
            use_container_width=True,
            disabled=not sel_atual,
            help="Remove todas as OAEs interditadas.",
            key="btn_limpar",
        ):
            st.session_state["interdicao_select"] = []
            st.rerun()

        # ---- Multiselect ----
        # Inicializa com a 1ª OAE pré-selecionada na 1ª vez que o app é aberto.
        if "interdicao_select" not in st.session_state:
            st.session_state["interdicao_select"] = piores[:1]

        interdicao = st.sidebar.multiselect(
            "OAEs interditadas (uma ou várias)",
            opcoes,
            key="interdicao_select",
            placeholder="Clique e escolha uma ou mais OAEs",
            help="Use o botão acima ou selecione manualmente. Cada OAE marcada será simulada como fechada.",
        )

        n_sel = len(interdicao)
        classe = "selection-counter" + (" empty" if n_sel == 0 else "")
        rotulo = "OAE selecionada" if n_sel == 1 else "OAEs selecionadas"
        st.sidebar.markdown(
            f"""
            <div class="{classe}">
                <span>🚫 <span class="count">{n_sel}</span> {rotulo}</span>
                <span class="total">de {len(opcoes)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---- Origem e destino ----
        st.sidebar.subheader("Origem e destino")
        disponiveis = [c for c in opcoes if c not in interdicao] or opcoes

        # Garante que valores em session_state sejam válidos para a lista atual
        if st.session_state.get("origem_sel") not in disponiveis:
            st.session_state["origem_sel"] = disponiveis[0]
        if st.session_state.get("destino_sel") not in disponiveis:
            st.session_state["destino_sel"] = disponiveis[-1] if len(disponiveis) > 1 else disponiveis[0]

        origem = st.sidebar.selectbox("Origem", disponiveis, key="origem_sel")
        destino = st.sidebar.selectbox("Destino", disponiveis, key="destino_sel")

        def _sortear_od(opcoes_sortear: list[str]) -> None:
            # Callback: roda ANTES do próximo render, então pode mexer
            # em session_state com chaves de widgets (origem_sel / destino_sel).
            if len(opcoes_sortear) >= 2:
                o, d = random.sample(opcoes_sortear, 2)
                st.session_state["origem_sel"] = o
                st.session_state["destino_sel"] = d

        st.sidebar.button(
            "🎲 Sortear origem/destino",
            use_container_width=True,
            disabled=len(disponiveis) < 2,
            help="Sorteia aleatoriamente um par origem/destino entre as OAEs não interditadas. "
                 "Útil para avaliar interferências em múltiplos cenários.",
            key="btn_random_od",
            on_click=_sortear_od,
            args=(disponiveis,),
        )

        # ---- Executar simulação + contador ----
        st.sidebar.markdown("---")
        executar = st.sidebar.button(
            "▶️ Executar simulação",
            use_container_width=True,
            type="primary",
        )

        sim_count = st.session_state.get("sim_count", 0)
        plural_sim = "simulação executada" if sim_count == 1 else "simulações executadas"
        st.sidebar.markdown(
            f"""
            <div class="sim-counter">
                <span>📊 {plural_sim}</span>
                <span class="count">{sim_count}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.sidebar.button(
            "🧹 Limpar contagem",
            use_container_width=True,
            disabled=sim_count == 0,
            help="Reinicia o contador e apaga o histórico de simulações desta sessão.",
            key="btn_limpar_sim",
        ):
            st.session_state["sim_count"] = 0
            st.session_state["simulacoes"] = []
            st.rerun()

    return {
        "usar_demo": usar_demo,
        "arquivo": arquivo,
        "modo_rede": modo_rede,
        "buffer_km": buffer_km,
        "mostrar_malha": mostrar_malha,
        "interdicao": interdicao,
        "origem": origem,
        "destino": destino,
        "executar": executar,
    }


def obter_ponto(df: pd.DataFrame, codigo: str) -> tuple[float, float]:
    linha = df[df["Código OAE"].astype(str) == str(codigo)].iloc[0]
    return float(linha["Latitude"]), float(linha["Longitude"])


def executar_simulacao(df: pd.DataFrame, opcoes: dict) -> dict | None:
    origem_cod = opcoes["origem"]
    destino_cod = opcoes["destino"]
    interdicao = opcoes["interdicao"] or []

    if origem_cod == destino_cod:
        st.warning("⚠️ Selecione OAEs **diferentes** para origem e destino.")
        return None

    try:
        o_lat, o_lon = obter_ponto(df, origem_cod)
        d_lat, d_lon = obter_ponto(df, destino_cod)
    except (KeyError, IndexError) as exc:
        st.error(f"❌ Não consegui localizar a OAE de origem/destino na base: {exc}")
        return None

    modo_forcado_simples = opcoes["modo_rede"].startswith("Forçar")
    coords_orig: list[tuple[float, float]] = []
    coords_alt: list[tuple[float, float]] = []
    dist_orig = dist_alt = 0.0
    modo_usado = "simplificado"
    G_osm = None
    malha_geojson = None

    with st.status("⏳ Executando simulação...", expanded=True) as status:
        try:
            # ----- Etapa 1: rede viária -----
            if modo_forcado_simples:
                st.write("• Modo simplificado **forçado** pelo usuário — pulando OSM.")
            else:
                area = _area_de_interesse(
                    df, interdicao, origem_cod, destino_cod, opcoes.get("buffer_km", 2)
                )
                if area is None:
                    st.write("  ✗ Não foi possível calcular a área — caindo para o simplificado.")
                else:
                    centro_lat, centro_lon, raio_m = area
                    st.write(
                        f"• Área de interesse: centro **({centro_lat:.4f}, {centro_lon:.4f})**, "
                        f"raio **{raio_m/1000:.2f} km** (auto + buffer {opcoes.get('buffer_km', 2)} km)."
                    )
                    st.write("• Baixando rede viária do OpenStreetMap...")
                    G_osm = construir_grafo_osm(centro_lat, centro_lon, raio_m)
                    if G_osm is not None:
                        st.write(f"  ✓ Rede OSM carregada ({G_osm.number_of_nodes()} nós, {G_osm.number_of_edges()} vias).")
                    else:
                        st.write("  ✗ OSM indisponível — caindo para o modo simplificado.")

            # ----- Etapa 2: rotas -----
            if G_osm is not None:
                st.write("• Mapeando OAEs interditadas para nós do grafo...")
                nos_remover: set[int] = set()
                for cod in interdicao:
                    lat, lon = obter_ponto(df, cod)
                    no = _no_mais_proximo(G_osm, lat, lon)
                    if no is not None:
                        nos_remover.add(no)
                st.write(f"  ✓ {len(nos_remover)} nó(s) marcado(s) para remoção.")

                st.write("• Calculando rota base (sem interdição)...")
                coords_orig, dist_orig = calcular_rota_osm(G_osm, (o_lat, o_lon), (d_lat, d_lon))
                st.write("• Calculando rota alternativa (com interdição)...")
                coords_alt, dist_alt = calcular_rota_osm(G_osm, (o_lat, o_lon), (d_lat, d_lon), nos_remover)

                st.write("• Extraindo malha viária para visualização...")
                malha_geojson = _extrair_malha_geojson(G_osm)
                st.write(f"  ✓ Malha com {len(malha_geojson.get('features', []))} segmentos.")
                modo_usado = "OSM"
            else:
                G_simp = construir_grafo_simplificado(df, k_vizinhos=3)
                st.write("• Calculando rotas no grafo simplificado...")
                coords_orig, dist_orig = calcular_rota_simplificada(G_simp, origem_cod, destino_cod)
                coords_alt, dist_alt = calcular_rota_simplificada(
                    G_simp, origem_cod, destino_cod, set(map(str, interdicao))
                )

            tem_alt = len(coords_alt) >= 2
            tem_orig = len(coords_orig) >= 2

            if not tem_orig and not tem_alt:
                status.update(label="❌ Nenhuma rota pôde ser calculada", state="error")
                st.error(
                    "Não foi possível calcular nenhuma rota — origem/destino podem estar "
                    "fora da área baixada do OSM. Tente aumentar o **Raio (km)** na sidebar "
                    "ou use o modo simplificado."
                )
                return None

            status.update(
                label=f"✓ Simulação concluída ({modo_usado})" + (
                    "" if tem_alt else " — sem rota alternativa"
                ),
                state="complete",
                expanded=False,
            )
        except Exception as exc:
            status.update(label="❌ Erro durante a simulação", state="error")
            st.error(f"Erro inesperado: `{type(exc).__name__}: {exc}`")
            return None

    if tem_alt:
        st.toast(f"✅ Simulação OK · modo {modo_usado}", icon="✅")
    else:
        st.toast("⚠️ Sem rota alternativa — todas as interditadas bloqueiam o par OD", icon="⚠️")

    cards_indicadores(
        total=len(df),
        interditadas=len(interdicao),
        dist_orig_m=dist_orig,
        dist_alt_m=dist_alt if tem_alt else 0.0,
        tem_alt=tem_alt,
    )

    st.markdown("### 🗺️ Comparativo de rotas")
    rotas = []
    if tem_orig:
        rotas.append({
            "coords": coords_orig,
            "color": "#E63946",  # vermelho — rota afetada pela interdição
            "label": "Rota original (afetada pela interdição)",
            "weight": 5,
            "dash_array": "10, 6",  # tracejada
        })
    if tem_alt:
        rotas.append({
            "coords": coords_alt,
            "color": "#22C55E",  # verde — nova rota proposta
            "label": "Rota alternativa (proposta)",
            "weight": 6,
            "opacity": 0.95,
        })

    mapa = desenhar_mapa(
        df,
        rotas=rotas,
        interditadas=interdicao,
        malha=malha_geojson,
        titulo=None,
    )
    folium.Marker(
        [o_lat, o_lon],
        tooltip=f"Origem: {origem_cod}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(mapa)
    folium.Marker(
        [d_lat, d_lon],
        tooltip=f"Destino: {destino_cod}",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
    ).add_to(mapa)
    st_folium(mapa, width=None, height=560, returned_objects=[])

    st.caption(
        f"**Modo de cálculo:** {modo_usado}  ·  "
        "🔵 **Malha viária** (rede OSM)  ·  "
        "🔴 **Rota original** afetada pela interdição (tracejada)  ·  "
        "🟢 **Rota alternativa** proposta."
    )

    return {
        "timestamp": datetime.now(),
        "origem": str(origem_cod),
        "destino": str(destino_cod),
        "interdicao": [str(c) for c in interdicao],
        "dist_orig_m": float(dist_orig),
        "dist_alt_m": float(dist_alt) if tem_alt else 0.0,
        "tem_alt": bool(tem_alt),
        "modo": modo_usado,
    }


def gerar_pdf_relatorio(df: pd.DataFrame, simulacoes: list[dict]) -> bytes:
    """Gera um relatório PDF consolidando todas as simulações da sessão."""
    from fpdf import FPDF

    def _txt(s: object) -> str:
        # Garante que a string é codificável em Latin-1 (suporta PT-BR).
        s = str(s)
        return s.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ----- Cabeçalho -----
    pdf.set_fill_color(15, 27, 51)
    pdf.rect(0, 0, 210, 24, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(10, 6)
    pdf.cell(0, 7, _txt("Relatório de Análise de Interdição de OAEs"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(10)
    pdf.cell(0, 5, _txt("Simulador de Resiliência da Rede Viária  ·  OAE-SIM v0.1"), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # ----- Metadados -----
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, _txt(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"), ln=True)
    pdf.cell(0, 5, _txt(f"Base carregada: {len(df)} OAEs"), ln=True)
    pdf.cell(0, 5, _txt(f"Total de simulações na sessão: {len(simulacoes)}"), ln=True)
    pdf.ln(3)

    if not simulacoes:
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, _txt(
            "Nenhuma simulação foi executada nesta sessão. "
            "Volte ao aplicativo, configure um cenário de interdição "
            "e execute pelo menos uma simulação antes de gerar o relatório."
        ))
        return bytes(pdf.output())

    # ----- Resumo executivo -----
    com_alt = sum(1 for s in simulacoes if s["tem_alt"])
    sem_alt = len(simulacoes) - com_alt
    incrementos_km = [
        (s["dist_alt_m"] - s["dist_orig_m"]) / 1000.0
        for s in simulacoes
        if s["tem_alt"] and s["dist_orig_m"] > 0
    ]
    incrementos_pct = [
        (s["dist_alt_m"] - s["dist_orig_m"]) / s["dist_orig_m"] * 100.0
        for s in simulacoes
        if s["tem_alt"] and s["dist_orig_m"] > 0
    ]
    avg_inc = sum(incrementos_km) / len(incrementos_km) if incrementos_km else 0
    max_inc = max(incrementos_km) if incrementos_km else 0
    avg_pct = sum(incrementos_pct) / len(incrementos_pct) if incrementos_pct else 0
    max_pct = max(incrementos_pct) if incrementos_pct else 0

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(0, 224, 212)
    pdf.cell(60, 7, _txt(" Resumo executivo"), fill=True, ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, _txt(
        f"- Cenários com rota alternativa: {com_alt} de {len(simulacoes)} "
        f"({com_alt/len(simulacoes)*100:.1f}%)"
    ), ln=True)
    pdf.cell(0, 5, _txt(f"- Cenários sem rota alternativa: {sem_alt}"), ln=True)
    pdf.cell(0, 5, _txt(f"- Aumento médio de distância: +{avg_inc:.2f} km ({avg_pct:+.1f}%)"), ln=True)
    pdf.cell(0, 5, _txt(f"- Aumento máximo observado: +{max_inc:.2f} km ({max_pct:+.1f}%)"), ln=True)
    pdf.ln(5)

    # ----- Detalhamento por simulação -----
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(0, 224, 212)
    pdf.cell(72, 7, _txt(" Detalhamento das simulações"), fill=True, ln=True)
    pdf.ln(2)

    headers = ["#", "Hora", "Origem", "Destino", "Intd.", "Modo", "Orig.(km)", "Alt.(km)", "Var.(%)"]
    widths  = [ 8,    18,     22,        22,         12,     18,      20,           20,         20]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(220, 230, 240)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _txt(h), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8.5)
    for i, s in enumerate(simulacoes, 1):
        hora = s["timestamp"].strftime("%H:%M:%S") if hasattr(s["timestamp"], "strftime") else str(s["timestamp"])
        var = "-"
        if s["tem_alt"] and s["dist_orig_m"] > 0:
            var = f"+{(s['dist_alt_m'] - s['dist_orig_m']) / s['dist_orig_m'] * 100:.1f}%"
        elif not s["tem_alt"]:
            var = "sem rota"
        row = [
            str(i),
            hora,
            s["origem"][:10],
            s["destino"][:10],
            str(len(s["interdicao"])),
            s["modo"],
            f"{s['dist_orig_m']/1000:.2f}" if s["dist_orig_m"] else "-",
            f"{s['dist_alt_m']/1000:.2f}" if s["tem_alt"] else "-",
            var,
        ]
        for c, w in zip(row, widths):
            pdf.cell(w, 5.5, _txt(c), border=1, align="C")
        pdf.ln()
    pdf.ln(4)

    # ----- Ranking de OAEs mais críticas -----
    impactos: dict[str, list[float]] = {}
    for s in simulacoes:
        if not s["tem_alt"] or s["dist_orig_m"] <= 0:
            continue
        var_pct = (s["dist_alt_m"] - s["dist_orig_m"]) / s["dist_orig_m"] * 100.0
        for oae in s["interdicao"]:
            impactos.setdefault(oae, []).append(var_pct)

    if impactos:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(0, 224, 212)
        pdf.cell(82, 7, _txt(" Ranking de OAEs mais críticas"), fill=True, ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 4.5, _txt(
            "Calculado como a variação percentual média de distância nos cenários "
            "em que cada OAE foi marcada como interditada. Quanto maior o valor, "
            "mais crítica é a OAE para a resiliência da rede."
        ))
        pdf.ln(1.5)

        ranked = sorted(impactos.items(), key=lambda x: -sum(x[1]) / len(x[1]))
        rank_headers = ["Posição", "Código OAE", "Aparições", "Var. média (%)", "Var. máxima (%)"]
        rank_widths  = [22,         32,           24,           36,                36]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 240)
        for h, w in zip(rank_headers, rank_widths):
            pdf.cell(w, 6, _txt(h), border=1, align="C", fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for pos, (oae, vars_) in enumerate(ranked[:10], 1):
            row = [
                f"{pos}",
                oae,
                str(len(vars_)),
                f"+{sum(vars_)/len(vars_):.1f}%",
                f"+{max(vars_):.1f}%",
            ]
            for c, w in zip(row, rank_widths):
                pdf.cell(w, 5.5, _txt(c), border=1, align="C")
            pdf.ln()
        pdf.ln(4)

    # ----- Metodologia -----
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(0, 6, _txt(" Metodologia"), fill=True, ln=True)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 4.5, _txt(
        "1) A rede viária é obtida do OpenStreetMap dentro de um raio configurável em "
        "torno do centroide das OAEs, ou substituída por uma rede simplificada "
        "(conexão por vizinhos mais próximos) quando o OSM não está disponível.\n\n"
        "2) Cada OAE interditada é mapeada para o nó mais próximo do grafo, e esses "
        "nós são removidos antes do cálculo do caminho alternativo.\n\n"
        "3) O caminho mínimo é calculado pelo algoritmo Dijkstra (NetworkX) usando o "
        "comprimento das vias como peso das arestas. A distância apresentada é em "
        "metros (convertida para km no relatório).\n\n"
        "4) A criticidade de uma OAE é estimada de forma empírica a partir do "
        "aumento percentual médio de distância nos cenários em que ela foi "
        "interditada. Trata-se de um indicador relativo, não absoluto."
    ))
    pdf.ln(2)

    # ----- Rodapé -----
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 130)
    pdf.cell(
        0, 5,
        _txt(f"Gerado por OAE-SIM v0.1 em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  ·  "
             f"github.com/luizaraujoengkil-ux/simulador-resiliencia-oae"),
        align="C",
    )

    return bytes(pdf.output())


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛣️", layout="wide")
    aplicar_estilo()
    cabecalho()
    cards_explicativos()
    st.markdown("")

    # Estado inicial
    if "df" not in st.session_state:
        st.session_state["df"] = pd.DataFrame()

    # Sidebar (precisa de df para popular seletores; mostramos placeholder primeiro)
    df_atual = st.session_state["df"]
    opcoes = sidebar_inputs(df_atual)

    # Decide qual base usar
    df_novo: pd.DataFrame = pd.DataFrame()
    arquivos = opcoes["arquivo"]
    if arquivos:
        # st.file_uploader com accept_multiple_files=True devolve lista; sem flag, um objeto.
        if not isinstance(arquivos, list):
            arquivos = [arquivos]
        partes = []
        for a in arquivos:
            d = carregar_arquivo(a)
            if not d.empty:
                partes.append(d)
        if partes:
            df_novo = pd.concat(partes, ignore_index=True)
            if df_novo["Código OAE"].duplicated().any():
                df_novo["Código OAE"] = (
                    df_novo["Código OAE"].astype(str)
                    + "_" + df_novo.groupby("Código OAE").cumcount().astype(str)
                )
                df_novo["Código OAE"] = df_novo["Código OAE"].str.replace(r"_0$", "", regex=True)
            st.sidebar.success(
                f"✓ {len(arquivos)} arquivo(s) consolidados — total: {len(df_novo)} OAEs"
            )
    elif opcoes["usar_demo"]:
        if SAMPLE_DATA_PATH.exists():
            df_novo = carregar_arquivo(SAMPLE_DATA_PATH)
        else:
            st.warning("Base de demonstração não encontrada em sample_data/oae_teste.csv.")

    if not df_novo.empty and not df_novo.equals(df_atual):
        st.session_state["df"] = df_novo
        st.rerun()

    df = st.session_state["df"]

    if df.empty:
        st.info(
            "Carregue uma base de OAEs ou ative **Usar base de demonstração** na barra lateral para iniciar."
        )
        return

    # Mapa geral — alvo do card "2. Visualizar mapa"
    interdicao_atual = opcoes.get("interdicao") or []
    st.markdown('<div id="mapa-criticidade"></div>', unsafe_allow_html=True)
    st.markdown("### 📍 Mapa geral de criticidade")

    if interdicao_atual:
        st.markdown(
            f"""
            <div class="legenda-destaque">
                <span class="badge">⛔ {len(interdicao_atual)}</span>
                <span><b>OAE(s) interditada(s)</b> aparecem no mapa com ícone preto de proibido.</span>
                <span class="legend-pill">🔴 crítica</span>
                <span class="legend-pill">🟠 ruim</span>
                <span class="legend-pill">🟡 regular</span>
                <span class="legend-pill">🟢 ótima</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            "Clique no botão **⛶** no canto superior direito do mapa para expandir em tela cheia. "
            "Cores indicam a Nota Geral de cada OAE."
        )

    # Tenta baixar a malha viária se o usuário ativou o toggle
    malha_geral = None
    if opcoes.get("mostrar_malha"):
        if not interdicao_atual:
            st.info(
                "ℹ️ **Selecione ao menos uma OAE interditada na sidebar** para carregar a malha viária. "
                "O raio é calculado automaticamente a partir do centroide **das OAEs interditadas** "
                "(origem/destino não entram no cálculo do mapa geral)."
            )
        else:
            # Mapa geral: área SÓ das interditadas (origem/destino NÃO entram)
            area = _area_de_interesse(
                df, interdicao_atual, origem=None, destino=None,
                buffer_km=opcoes.get("buffer_km", 2),
            )
            if area is None:
                st.warning("⚠️ Não foi possível calcular a área a partir das OAEs selecionadas.")
            else:
                centro_lat, centro_lon, raio_m = area
                with st.spinner(
                    f"🌐 Baixando malha do OSM · centro ({centro_lat:.4f}, {centro_lon:.4f}) · "
                    f"raio {raio_m/1000:.2f} km..."
                ):
                    G_geral = construir_grafo_osm(centro_lat, centro_lon, raio_m)
                if G_geral is not None:
                    malha_geral = _extrair_malha_geojson(G_geral)
                    n_int = len(interdicao_atual)
                    triang = (
                        f"centroide da OAE interditada + buffer {opcoes.get('buffer_km', 2)} km"
                        if n_int == 1 else
                        f"triangulação das {n_int} OAEs interditadas + buffer {opcoes.get('buffer_km', 2)} km"
                    )
                    st.caption(
                        f"🌐 Malha OSM: **{G_geral.number_of_nodes()} nós · "
                        f"{G_geral.number_of_edges()} vias** em **raio {raio_m/1000:.2f} km** "
                        f"({triang})."
                    )
                else:
                    st.warning(
                        "⚠️ Não foi possível baixar a malha (sem internet ou área inválida). "
                        "Desative o toggle 🌐 ou tente novamente."
                    )

    mapa_geral = desenhar_mapa(df, interditadas=interdicao_atual, malha=malha_geral, titulo=None)
    st_folium(mapa_geral, width=None, height=520, returned_objects=[])

    # ----- Cenário de interdição atual — alvo do card "3. Selecionar interdição"
    st.markdown('<div id="cenario-interdicao"></div>', unsafe_allow_html=True)
    st.markdown("### 🚫 Cenário de interdição atual")

    if interdicao_atual:
        n_int = len(interdicao_atual)
        plural = "OAE interditada" if n_int == 1 else "OAEs interditadas"
        st.markdown(
            f"""
            <div class="interdicao-banner">
                <span class="emoji">⛔</span>
                <span class="count">{n_int}</span>
                <span class="label">{plural}</span>
                <span class="total">de {len(df)} no total</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        df_int = df[df["Código OAE"].astype(str).isin([str(c) for c in interdicao_atual])]
        cols_int = [c for c in ["Código OAE", "Tipo", "Rodovia / Trecho", "Município / UF", "Nota Geral"]
                    if c in df_int.columns]
        st.dataframe(
            df_int[cols_int],
            use_container_width=True,
            hide_index=True,
            height=min(320, 60 + n_int * 36),
        )
    else:
        st.markdown(
            """
            <div class="empty-state">
                <div class="big-emoji">✋</div>
                <div class="big-text">Nenhuma OAE interditada no cenário atual</div>
                <div class="small-text">
                    Use o painel lateral em <b>Interdição</b> para marcar uma ou mais OAEs como fechadas.
                    Você pode aplicar o filtro de "piores notas" ou escolher manualmente.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ----- Planilha de dados — alvo do card "1. Carregar base"
    st.markdown('<div id="planilha-dados"></div>', unsafe_allow_html=True)
    st.markdown("### 📋 Planilha de dados das OAEs")
    st.caption(
        f"Dados que estão sendo usados na simulação — {len(df)} OAEs carregadas. "
        f"Confira aqui se a base bate com o que você espera antes de rodar o cenário."
    )
    cols_show = [c for c in COLUNAS_OBRIGATORIAS + COLUNAS_OPCIONAIS if c in df.columns]
    st.dataframe(df[cols_show], use_container_width=True, hide_index=True, height=300)

    # Simulação
    st.markdown("---")
    st.markdown("### 🚦 Simulação de interdição")
    if opcoes["executar"]:
        if not opcoes["interdicao"]:
            st.warning("Selecione pelo menos uma OAE para interditar antes de executar.")
        else:
            resultado = executar_simulacao(df, opcoes)
            if resultado is not None:
                st.session_state.setdefault("simulacoes", []).append(resultado)
                st.session_state["sim_count"] = st.session_state.get("sim_count", 0) + 1
    else:
        st.markdown(
            '<div class="small-note">Selecione OAEs para interditar, defina origem e destino '
            'e clique em <b>Executar simulação</b> na barra lateral.</div>',
            unsafe_allow_html=True,
        )

    # ----- Relatório consolidado — alvo do card "4. Calcular impacto"
    st.markdown("---")
    st.markdown('<div id="relatorio"></div>', unsafe_allow_html=True)
    st.markdown("### 📊 Relatório consolidado e exportação")

    simulacoes = st.session_state.get("simulacoes", [])
    if not simulacoes:
        st.markdown(
            """
            <div class="empty-state">
                <div class="big-emoji">📭</div>
                <div class="big-text">Nenhuma simulação executada nesta sessão</div>
                <div class="small-text">
                    Configure um cenário de interdição na <b>barra lateral</b> e clique em
                    <b>Executar simulação</b>. Você pode rodar vários cenários
                    (use o botão <b>🎲 Sortear origem/destino</b> para variar) e ao final
                    baixar o relatório PDF aqui.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Métricas agregadas
        com_alt = sum(1 for s in simulacoes if s["tem_alt"])
        incs = [
            (s["dist_alt_m"] - s["dist_orig_m"]) / 1000.0
            for s in simulacoes
            if s["tem_alt"] and s["dist_orig_m"] > 0
        ]
        avg = sum(incs) / len(incs) if incs else 0.0
        mx = max(incs) if incs else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(
            f'<div class="metric-card"><div class="label">Total de simulações</div>'
            f'<div class="value">{len(simulacoes)}</div></div>',
            unsafe_allow_html=True,
        )
        m2.markdown(
            f'<div class="metric-card"><div class="label">Com rota alternativa</div>'
            f'<div class="value">{com_alt}</div></div>',
            unsafe_allow_html=True,
        )
        m3.markdown(
            f'<div class="metric-card"><div class="label">Aumento médio</div>'
            f'<div class="value">+{avg:.2f} km</div></div>',
            unsafe_allow_html=True,
        )
        m4.markdown(
            f'<div class="metric-card"><div class="label">Aumento máximo</div>'
            f'<div class="value">+{mx:.2f} km</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("")
        st.markdown("**Histórico das simulações desta sessão**")
        hist = pd.DataFrame([
            {
                "#": i + 1,
                "Hora": s["timestamp"].strftime("%H:%M:%S") if hasattr(s["timestamp"], "strftime") else str(s["timestamp"]),
                "Origem": s["origem"],
                "Destino": s["destino"],
                "Interditadas": len(s["interdicao"]),
                "Modo": s["modo"],
                "Dist. orig. (km)": round(s["dist_orig_m"] / 1000, 2) if s["dist_orig_m"] else None,
                "Dist. alt. (km)":  round(s["dist_alt_m"]  / 1000, 2) if s["tem_alt"] else None,
                "Var. (%)": (
                    round((s["dist_alt_m"] - s["dist_orig_m"]) / s["dist_orig_m"] * 100, 1)
                    if s["tem_alt"] and s["dist_orig_m"] else None
                ),
            }
            for i, s in enumerate(simulacoes)
        ])
        st.dataframe(hist, use_container_width=True, hide_index=True, height=min(320, 50 + len(hist) * 36))

        col_dl, col_clear = st.columns([3, 1])
        try:
            pdf_bytes = gerar_pdf_relatorio(df, simulacoes)
            col_dl.download_button(
                "📄 Baixar relatório completo em PDF",
                data=pdf_bytes,
                file_name=f"relatorio_oae_{datetime.now():%Y%m%d_%H%M%S}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                help="Gera um PDF com resumo executivo, detalhamento de todas as simulações, "
                     "ranking de OAEs mais críticas e metodologia.",
            )
        except Exception as exc:
            col_dl.error(f"Erro ao gerar PDF: {exc}")

        if col_clear.button("🧹 Limpar histórico", use_container_width=True, key="btn_clear_hist"):
            st.session_state["simulacoes"] = []
            st.session_state["sim_count"] = 0
            st.rerun()


if __name__ == "__main__":
    main()
