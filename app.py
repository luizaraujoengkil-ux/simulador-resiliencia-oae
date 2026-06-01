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
DATA_DIR = Path(__file__).parent / "data"

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
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stDownloadButton"] button {
            background: linear-gradient(90deg, #00E0D4, #1E6091);
            color: #07111F;
            font-weight: 700;
            border-radius: 8px;
            border: none;
            padding: 0.45rem 1rem;
            font-size: 0.88rem;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stDownloadButton"] button:hover {
            filter: brightness(1.08);
            color: #07111F;
        }
        .stButton > button:disabled,
        .stDownloadButton > button:disabled {
            background: #1F2D4A;
            color: #6B7A99;
            filter: none;
        }
        /* Uploader "Browse files" — mantém escuro com borda teal */
        [data-testid="stFileUploaderDropzone"] button {
            background: #0F1B33 !important;
            color: #00E0D4 !important;
            border: 1px solid #00E0D4 !important;
        }
        /* Rodapé com autor / licença */
        .app-footer {
            margin-top: 2rem;
            padding: 0.9rem 1rem;
            border-top: 1px solid #1F2D4A;
            font-size: 0.78rem;
            color: #8FA0BA;
            text-align: center;
            line-height: 1.5;
        }
        .app-footer a { color: #00E0D4; text-decoration: none; }
        .app-footer a:hover { text-decoration: underline; }

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
        df["Tipo"] = "Ponte"
    df["Tipo"] = df["Tipo"].fillna("Ponte").astype(str)

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


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _reverse_geocode(lat: float, lon: float) -> dict | None:
    """Reverse geocoding via Nominatim (OpenStreetMap). Cacheado por 24 h.

    Devolve o dict `address` completo retornado pela API, ou None em caso de erro.
    Respeita o uso aceitável: User-Agent identificável, 1 req/s no caller.
    """
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(
            user_agent="simulador-resiliencia-oae/0.1 (github.com/luizaraujoengkil-ux/simulador-resiliencia-oae)",
            timeout=10,
        )
        location = geolocator.reverse(f"{lat}, {lon}", language="pt-BR", zoom=17)
        if location and isinstance(location.raw, dict):
            return location.raw.get("address") or {}
    except Exception:
        return None
    return None


def _vazio_geo(s: object) -> bool:
    """True se o campo está vazio/placeholder e merece geocoding."""
    return str(s).strip().lower() in ("", "nan", "none", "não informado", "nao informado")


def _extrair_municipio_rodovia(addr: dict) -> tuple[str | None, str | None]:
    """Extrai 'Cidade / UF' e 'ref / road' do address dict do Nominatim."""
    if not addr:
        return None, None
    cidade = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("suburb")
    )
    uf = (
        (addr.get("ISO3166-2-lvl4", "").split("-")[-1] if addr.get("ISO3166-2-lvl4") else "")
        or addr.get("state_code", "")
    )
    municipio = (f"{cidade} / {uf}" if uf else cidade) if cidade else None

    ref = (addr.get("ref") or "").strip()
    road = (addr.get("road") or "").strip()
    if ref and road:
        rodovia = f"{ref} / {road}"
    elif ref:
        rodovia = ref
    elif road:
        rodovia = road
    else:
        rodovia = None
    return municipio, rodovia


def _aplicar_cache_enrichment(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica enrichment do session_state ao DataFrame (in-place, idempotente)."""
    if df.empty:
        return df
    cache = st.session_state.get("enrichment_cache", {})
    if not cache:
        return df
    df = df.copy()
    if "Município / UF" not in df.columns:
        df["Município / UF"] = "Não informado"
    if "Rodovia / Trecho" not in df.columns:
        df["Rodovia / Trecho"] = "Não informado"
    for idx in df.index:
        try:
            lat = float(df.at[idx, "Latitude"])
            lon = float(df.at[idx, "Longitude"])
        except (TypeError, ValueError):
            continue
        key = (round(lat, 5), round(lon, 5))
        info = cache.get(key)
        if not info:
            continue
        if info.get("municipio") and _vazio_geo(df.at[idx, "Município / UF"]):
            df.at[idx, "Município / UF"] = info["municipio"]
        if info.get("rodovia") and _vazio_geo(df.at[idx, "Rodovia / Trecho"]):
            df.at[idx, "Rodovia / Trecho"] = info["rodovia"]
    return df


def enriquecer_geocodificacao_auto(df: pd.DataFrame) -> pd.DataFrame:
    """Versão NATIVA: aplica cache primeiro, depois geocodifica o que falta.

    Roda automaticamente após carregar os dados. Cada (lat, lon) é tentada uma
    única vez por sessão (track em session_state['geocoding_attempted']).
    O cache persiste durante a sessão em session_state['enrichment_cache'].
    """
    if df.empty:
        return df

    df = _aplicar_cache_enrichment(df)

    if "Município / UF" not in df.columns:
        df["Município / UF"] = "Não informado"
    if "Rodovia / Trecho" not in df.columns:
        df["Rodovia / Trecho"] = "Não informado"

    cache = st.session_state.setdefault("enrichment_cache", {})
    attempted = st.session_state.setdefault("geocoding_attempted", set())

    pendentes: list[tuple] = []  # [(idx, key, lat, lon, codigo)]
    for idx in df.index:
        try:
            lat = float(df.at[idx, "Latitude"])
            lon = float(df.at[idx, "Longitude"])
            key = (round(lat, 5), round(lon, 5))
        except (TypeError, ValueError):
            continue
        if key in attempted:
            continue
        if _vazio_geo(df.at[idx, "Município / UF"]) or _vazio_geo(df.at[idx, "Rodovia / Trecho"]):
            codigo = str(df.at[idx, "Código OAE"])
            pendentes.append((idx, key, lat, lon, codigo))

    if not pendentes:
        return df

    import time as _time

    progress = st.progress(
        0.0,
        text=f"🌐 Preenchendo Município e Rodovia via OpenStreetMap ({len(pendentes)} OAE(s))...",
    )

    for i, (idx, key, lat, lon, codigo) in enumerate(pendentes):
        progress.progress(
            (i + 0.3) / len(pendentes),
            text=f"🌐 ({i+1}/{len(pendentes)}) consultando {codigo}...",
        )
        addr = _reverse_geocode(lat, lon)
        attempted.add(key)

        if addr:
            municipio, rodovia = _extrair_municipio_rodovia(addr)
            cache[key] = {"municipio": municipio, "rodovia": rodovia}
            if municipio and _vazio_geo(df.at[idx, "Município / UF"]):
                df.at[idx, "Município / UF"] = municipio
            if rodovia and _vazio_geo(df.at[idx, "Rodovia / Trecho"]):
                df.at[idx, "Rodovia / Trecho"] = rodovia

        progress.progress((i + 1) / len(pendentes), text=f"🌐 ({i+1}/{len(pendentes)}) {codigo} ok")
        _time.sleep(1.05)  # Nominatim rate limit: 1 req/s

    progress.empty()
    return df


def _nos_dentro_raio(G, lat: float, lon: float, raio_m: float) -> set[int]:
    """Retorna o conjunto de nós OSM dentro de `raio_m` metros de (lat, lon)."""
    nos = set()
    for n, data in G.nodes(data=True):
        try:
            d = _haversine_m(lat, lon, data["y"], data["x"])
        except (KeyError, TypeError):
            continue
        if d <= raio_m:
            nos.add(n)
    return nos


def _arestas_dentro_raio(G, lat: float, lon: float, raio_m: float) -> set[tuple]:
    """Retorna o conjunto de arestas (u, v, key) cuja geometria passa a menos
    de `raio_m` metros do ponto (lat, lon).

    Usa shapely para distância ponto-segmento. Funciona com arestas que têm
    geometria explícita (LineString) ou apenas straight line entre nós.
    """
    from shapely.geometry import Point, LineString

    pt = Point(lon, lat)
    # Conversão graus → metros (aproximada para a latitude local)
    lat_rad = math.radians(lat)
    metros_por_grau_lat = 111_320.0
    metros_por_grau_lon = 111_320.0 * math.cos(lat_rad)
    metros_por_grau = (metros_por_grau_lat + metros_por_grau_lon) / 2.0
    raio_graus = raio_m / metros_por_grau

    arestas = set()
    for u, v, key, data in G.edges(keys=True, data=True):
        geom = data.get("geometry")
        if geom is None:
            try:
                geom = LineString(
                    [
                        (G.nodes[u]["x"], G.nodes[u]["y"]),
                        (G.nodes[v]["x"], G.nodes[v]["y"]),
                    ]
                )
            except (KeyError, TypeError):
                continue
        try:
            d_graus = geom.distance(pt)
        except Exception:
            continue
        if d_graus <= raio_graus:
            arestas.add((u, v, key))
    return arestas


def _auto_od_da_oae(
    G,
    oae_lat: float,
    oae_lon: float,
    raio_min_m: float = 30.0,
    raio_max_m: float = 3000.0,
) -> tuple[tuple[float, float], tuple[float, float], dict] | None:
    """Deriva par (Origem, Destino) automaticamente para uma OAE no grafo OSM.

    Estratégia (simplificada para ser robusta):
    1. Coleta todos os nós entre `raio_min_m` e `raio_max_m` da OAE.
    2. Pega o nó mais próximo como **origem** (fora da zona de remoção).
    3. Procura, entre os 300 mais próximos, o nó cuja direção a partir da OAE
       é mais **oposta** à da origem — esse vira o **destino**.

    Retorna ((origem_lat, lon), (destino_lat, lon), diagnostico_dict) ou None.
    """
    candidatos: list[tuple[int, float, float]] = []
    n_total = 0
    n_no_raio_min = 0
    n_acima_raio_max = 0
    erros = 0

    for n, data in G.nodes(data=True):
        n_total += 1
        try:
            d = _haversine_m(oae_lat, oae_lon, data["y"], data["x"])
        except Exception:
            erros += 1
            continue
        if d < raio_min_m:
            n_no_raio_min += 1
            continue
        if d > raio_max_m:
            n_acima_raio_max += 1
            continue
        ang = math.atan2(data["y"] - oae_lat, data["x"] - oae_lon)
        candidatos.append((n, d, ang))

    diagnostico = {
        "n_total": n_total,
        "n_candidatos": len(candidatos),
        "n_dentro_raio_min": n_no_raio_min,
        "n_acima_raio_max": n_acima_raio_max,
        "erros_haversine": erros,
        "raio_min_m": raio_min_m,
        "raio_max_m": raio_max_m,
    }

    if len(candidatos) < 2:
        return None, diagnostico  # type: ignore[return-value]

    # Ordena por distância e mantém só os 300 mais próximos (O(N²) seguro)
    candidatos.sort(key=lambda x: x[1])
    if len(candidatos) > 300:
        candidatos = candidatos[:300]

    # Origem = o nó mais próximo (que sobreviveu ao raio_min)
    n1, d1, a1 = candidatos[0]

    # Destino = o nó com direção mais oposta a a1
    melhor_n2 = None
    melhor_score = -1.0
    for n2, d2, a2 in candidatos[1:]:
        diff = abs(a1 - a2)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        # Score: angular (max π ≈ 3.14) - penalidade pequena por distância
        score = diff - 0.0003 * d2
        if score > melhor_score:
            melhor_score = score
            melhor_n2 = n2

    if melhor_n2 is None:
        return None, diagnostico  # type: ignore[return-value]

    p1 = (G.nodes[n1]["y"], G.nodes[n1]["x"])
    p2 = (G.nodes[melhor_n2]["y"], G.nodes[melhor_n2]["x"])
    return p1, p2, diagnostico


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
    arestas_remover: set[tuple] | None = None,
) -> tuple[list[tuple[float, float]], float]:
    """Calcula caminho mais curto. Retorna (coords [(lat,lon)...], distancia_m).

    Tanto nós quanto arestas podem ser removidos antes do cálculo. Para
    interdição cirúrgica de pontes/viadutos, prefira remover arestas
    (mantém os nós das intersecções acessíveis por outras vias).
    """
    H = G
    if nos_remover or arestas_remover:
        H = G.copy()
        if nos_remover:
            H.remove_nodes_from([n for n in nos_remover if n in H.nodes])
        if arestas_remover:
            for edge in arestas_remover:
                # edge é (u, v, key)
                if len(edge) == 3:
                    u, v, k = edge
                    if H.has_edge(u, v, k):
                        H.remove_edge(u, v, k)
                else:
                    u, v = edge[0], edge[1]
                    if H.has_edge(u, v):
                        H.remove_edge(u, v)

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
    raio_km: float | None = None,
) -> None:
    delta_m = (dist_alt_m - dist_orig_m) if (dist_orig_m and dist_alt_m) else 0.0
    # NOVO: Impacto % = quanto da rota alternativa é DESVIO causado pela interdição
    # Naturalmente bounded entre 0 e ~100%: 0=rotas iguais, 90%=alt é 10x maior, etc.
    impacto_pct = (delta_m / dist_alt_m * 100) if dist_alt_m else 0.0
    fator = (dist_alt_m / dist_orig_m) if (dist_orig_m and dist_alt_m) else 0.0

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
        ("Impacto %", f"{impacto_pct:.1f}%" if tem_alt else "—"),
        ("Fator (×)", f"{fator:.2f}×" if tem_alt and dist_orig_m else "—"),
    ]

    cols = st.columns(len(indicadores))
    for col, (label, valor) in zip(cols, indicadores):
        col.markdown(
            f'<div class="metric-card"><div class="label">{label}</div>'
            f'<div class="value">{valor}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(f"**Status da rede:** {status_html}", unsafe_allow_html=True)

    # Sugestão clara quando NÃO ACHOU rota alternativa
    if not tem_alt:
        raio_txt = f"{raio_km:.1f} km" if raio_km else "configurado"
        st.error(
            f"❌ **Nenhuma rota alternativa encontrada** com raio de **{raio_txt}**. "
            f"A área baixada do OSM pode ser pequena demais para revelar contornos. "
            f"**Aumente o slider 'Buffer (km) ao redor da área de interesse' na sidebar** "
            f"(tente 5-10 km) e rode a simulação novamente. "
            f"Se preferir, pode remover esta tentativa do histórico depois — botão no relatório consolidado."
        )

    # Aviso quando a baseline é curta: porcentagens viram extremas
    if tem_alt and 0 < dist_orig_m < 1000:
        st.warning(
            f"⚠️ **Baseline curta** ({_fmt_km(dist_orig_m)}). Origem e destino "
            f"foram derivados muito perto da OAE focal — ideal para medir impacto "
            f"**hyperlocal**. Aumento absoluto: **{_fmt_km(delta_m)}**, "
            f"Fator: **{fator:.2f}×**."
        )


# ----------------------------------------------------------------------------
# UI principal
# ----------------------------------------------------------------------------

def _renderiza_contador_sim(slot) -> None:
    """Renderiza o contador 'X simulações executadas' no placeholder fornecido.
    Pode ser chamado várias vezes — cada chamada substitui o conteúdo do slot."""
    sim_count = st.session_state.get("sim_count", 0)
    plural = "simulação executada" if sim_count == 1 else "simulações executadas"
    slot.markdown(
        f"""
        <div class="sim-counter">
            <span>📊 {plural}</span>
            <span class="count">{sim_count}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_inputs(df: pd.DataFrame) -> dict:
    """Renderiza a sidebar e devolve as escolhas do usuário."""
    st.sidebar.header("⚙️ Controles")

    # Detecta arquivos disponíveis na pasta data/ (já comitados no repositório)
    arquivos_locais = []
    if DATA_DIR.exists():
        for ext in ("*.kmz", "*.kml", "*.csv", "*.xlsx", "*.xls"):
            arquivos_locais.extend(sorted(DATA_DIR.glob(ext)))

    opcoes_fonte = ["🧪 Base de demonstração"]
    if arquivos_locais:
        opcoes_fonte.append(f"📂 Pasta data/ ({len(arquivos_locais)} arquivos)")
    opcoes_fonte.append("📤 Upload manual")

    fonte = st.sidebar.radio(
        "Fonte de dados",
        opcoes_fonte,
        index=1 if len(opcoes_fonte) == 3 else 0,  # se há data/, default = data/
        help="Demo: base fictícia do ES. data/: arquivos versionados no repo. Upload: enviar agora.",
    )

    arquivo = None
    arquivos_data_paths: list[Path] = []
    usar_demo = "demonstração" in fonte

    if "Pasta data/" in fonte and arquivos_locais:
        import hashlib
        nomes = [p.name for p in arquivos_locais]
        # "Impressão digital" da lista atual: muda sempre que algum arquivo é
        # adicionado/renomeado/removido. Isso vira a key do multiselect, então
        # arquivos novos sempre entram já marcados (estado anterior é descartado).
        fingerprint = hashlib.md5(",".join(sorted(nomes)).encode()).hexdigest()[:10]
        selecionados = st.sidebar.multiselect(
            "Arquivos a carregar",
            options=nomes,
            default=nomes,
            help="Desmarque os que não quiser usar agora. Novos arquivos colocados em "
                 "data/ aparecem aqui automaticamente após refresh (já marcados).",
            key=f"ms_data_{fingerprint}",
        )
        arquivos_data_paths = [p for p in arquivos_locais if p.name in selecionados]
        st.sidebar.caption(
            f"📂 {len(arquivos_data_paths)} de {len(arquivos_locais)} arquivo(s) marcado(s) "
            f"· lista re-escaneada a cada refresh da página."
        )
    elif "Upload" in fonte:
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
        else:
            # Sanity check: remove códigos órfãos (ex.: KMZ renomeado, base
            # nova com nomes diferentes). Streamlit não filtra sozinho e o
            # selectbox/multiselect quebra com valores fora das opções.
            atual = st.session_state["interdicao_select"]
            validos = [c for c in atual if c in opcoes]
            if validos != atual:
                st.session_state["interdicao_select"] = validos or piores[:1]

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

        # ---- OAE focal para análise de impacto local ----
        # Modelo: a simulação mede quanto um veículo que PRECISA cruzar esta OAE
        # rodaria a mais caso ela esteja interditada. Origem/destino são pontos
        # sintéticos da própria via, ~30–300 m de cada lado da OAE focal.
        st.sidebar.subheader("Análise de impacto local")
        if not interdicao:
            st.sidebar.markdown(
                """
                <div class="empty-state" style="padding:0.8rem;text-align:left;">
                    <div class="small-text">
                        Selecione ao menos 1 OAE interditada acima.
                        Os pontos de origem e destino da análise são derivados
                        <b>automaticamente</b> dos lados da OAE focal.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            origem = None
            destino = None
        else:
            # Limpa valor stale do session_state se não estiver mais nas opções
            if (
                "oae_focal_sel" in st.session_state
                and st.session_state["oae_focal_sel"] not in interdicao
            ):
                st.session_state["oae_focal_sel"] = interdicao[0]
            origem = st.sidebar.selectbox(
                "OAE focal da análise",
                interdicao,
                help="A simulação responde: 'se eu PRECISASSE atravessar esta OAE, "
                     "quanto a viagem ficaria mais longa caso ela esteja interditada?'. "
                     "Origem e destino são pontos sintéticos da própria via, em lados "
                     "opostos da OAE — não representam viagens reais de origem/destino "
                     "urbanas.",
                key="oae_focal_sel",
            )
            # Mantemos a chave 'destino' por compatibilidade com o restante do código.
            destino = origem
            st.sidebar.caption(
                "ℹ️ **Escopo:** impacto local da travessia. Origem e destino são "
                "calculados em pontos da via, de ~30 a 300 m de cada lado da OAE focal."
            )

        # ---- Executar simulação + contador ----
        st.sidebar.markdown("---")
        executar = st.sidebar.button(
            "▶️ Executar simulação",
            use_container_width=True,
            type="primary",
        )

        # Placeholder do contador — pode ser atualizado depois da simulação
        # via _atualizar_contador_sidebar() sem precisar de st.rerun().
        counter_slot = st.sidebar.empty()
        _renderiza_contador_sim(counter_slot)

        sim_count = st.session_state.get("sim_count", 0)
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
        "arquivos_data_paths": arquivos_data_paths,
        "modo_rede": modo_rede,
        "buffer_km": buffer_km,
        "mostrar_malha": mostrar_malha,
        "interdicao": interdicao,
        "origem": origem,
        "destino": destino,
        "executar": executar,
        "counter_slot": counter_slot if not df.empty else None,
    }


def obter_ponto(df: pd.DataFrame, codigo: str) -> tuple[float, float]:
    linha = df[df["Código OAE"].astype(str) == str(codigo)].iloc[0]
    return float(linha["Latitude"]), float(linha["Longitude"])


def executar_simulacao(df: pd.DataFrame, opcoes: dict) -> dict | None:
    interdicao = opcoes["interdicao"] or []
    oae_focal = opcoes.get("origem")  # agora é o código da OAE focal (escolhida na sidebar)

    if not oae_focal or oae_focal not in interdicao:
        # garante uma OAE focal válida (default: primeira interditada)
        if interdicao:
            oae_focal = interdicao[0]
        else:
            st.warning("⚠️ Selecione ao menos 1 OAE interditada na sidebar.")
            return None

    try:
        oae_lat, oae_lon = obter_ponto(df, oae_focal)
    except (KeyError, IndexError) as exc:
        st.error(f"❌ Não consegui localizar a OAE focal **{oae_focal}** na base: {exc}")
        return None

    modo_forcado_simples = opcoes["modo_rede"].startswith("Forçar")
    coords_orig: list[tuple[float, float]] = []
    coords_alt: list[tuple[float, float]] = []
    dist_orig = dist_alt = 0.0
    modo_usado = "simplificado"
    G_osm = None
    malha_geojson = None
    raio_usado_m: float | None = None
    # Origem/destino são derivados automaticamente; começam com a posição da OAE
    o_lat = d_lat = oae_lat
    o_lon = d_lon = oae_lon

    with st.status("⏳ Executando simulação...", expanded=True) as status:
        try:
            # ----- Etapa 1: rede viária -----
            if modo_forcado_simples:
                st.write("• Modo simplificado **forçado** pelo usuário — pulando OSM.")
            else:
                # Área inclui apenas as OAEs interditadas (OD será derivado depois)
                area = _area_de_interesse(
                    df, interdicao, origem=None, destino=None,
                    buffer_km=opcoes.get("buffer_km", 2),
                )
                if area is None:
                    st.write("  ✗ Não foi possível calcular a área — caindo para o simplificado.")
                else:
                    centro_lat, centro_lon, raio_m = area
                    raio_usado_m = raio_m
                    st.write(
                        f"• Área de interesse: centro **({centro_lat:.4f}, {centro_lon:.4f})**, "
                        f"raio **{raio_m/1000:.2f} km** (centroide das interditadas + buffer "
                        f"{opcoes.get('buffer_km', 2)} km)."
                    )
                    st.write("• Baixando rede viária do OpenStreetMap...")
                    G_osm = construir_grafo_osm(centro_lat, centro_lon, raio_m)
                    if G_osm is not None:
                        st.write(f"  ✓ Rede OSM carregada ({G_osm.number_of_nodes()} nós, {G_osm.number_of_edges()} vias).")
                    else:
                        st.write("  ✗ OSM indisponível — caindo para o modo simplificado.")

            # ----- Etapa 2: rotas -----
            if G_osm is not None:
                # raio_min_m=200 garante que o OD fique FORA da zona de bloqueio
                # (cada OAE remove ~100m), mesmo quando há várias interditadas próximas.
                # Resultado: rotas alternativas seguem caminhos mais naturais (ex: usar
                # uma ponte vizinha em vez de fazer detour gigante).
                st.write(f"• Derivando OD a partir da OAE focal **{oae_focal}** (faixa 200 m – 5 km)...")
                resultado_od = _auto_od_da_oae(G_osm, oae_lat, oae_lon, raio_min_m=200.0, raio_max_m=5000.0)
                if resultado_od[0] is None:
                    # Falhou — mostra diagnóstico detalhado
                    diag = resultado_od[1]
                    status.update(label="❌ Não consegui derivar OD da OAE focal", state="error")
                    st.error(
                        f"**Falha ao derivar origem/destino para {oae_focal}.**\n\n"
                        f"Diagnóstico do grafo OSM (posição da OAE: "
                        f"`({oae_lat:.5f}, {oae_lon:.5f})`):\n"
                        f"- Total de nós no grafo: **{diag['n_total']}**\n"
                        f"- Candidatos válidos (entre {diag['raio_min_m']:.0f} m e "
                        f"{diag['raio_max_m']:.0f} m da OAE): **{diag['n_candidatos']}**\n"
                        f"- Nós muito perto (< {diag['raio_min_m']:.0f} m, na zona removida): "
                        f"**{diag['n_dentro_raio_min']}**\n"
                        f"- Nós muito longe (> {diag['raio_max_m']:.0f} m): "
                        f"**{diag['n_acima_raio_max']}**\n"
                        f"- Erros de cálculo: **{diag['erros_haversine']}**\n\n"
                        f"**O que tentar:** aumentar o **Buffer (km)** na sidebar para baixar "
                        f"uma área maior, ou escolher outra OAE focal."
                    )
                    return None
                (o_lat, o_lon), (d_lat, d_lon), diag = resultado_od
                d_o = _haversine_m(oae_lat, oae_lon, o_lat, o_lon)
                d_d = _haversine_m(oae_lat, oae_lon, d_lat, d_lon)
                st.write(
                    f"  ✓ {diag['n_candidatos']} candidatos · "
                    f"Origem a **{d_o:.0f} m** da OAE · Destino a **{d_d:.0f} m**"
                )

                st.write("• Identificando arestas a bloquear (raio = 100 m)...")
                # Removemos ARESTAS (não nós): isola exatamente as faixas da
                # ponte sem desconectar intersecções vizinhas. Captura corretamente
                # pistas duplicadas (avenida ida+volta) e geometrias curvas.
                raio_bloqueio_m = 100.0
                arestas_remover: set[tuple] = set()
                for cod in interdicao:
                    lat, lon = obter_ponto(df, cod)
                    bloco = _arestas_dentro_raio(G_osm, lat, lon, raio_bloqueio_m)
                    arestas_remover |= bloco
                st.write(
                    f"  ✓ {len(arestas_remover)} aresta(s) marcada(s) para remoção "
                    f"({len(interdicao)} OAE(s) × ~{len(arestas_remover)//max(1,len(interdicao))} arestas cada)."
                )
                # `nos_remover` mantido vazio (apenas para compat)
                nos_remover: set[int] = set()

                st.write("• Calculando rota base (sem interdição)...")
                coords_orig, dist_orig = calcular_rota_osm(G_osm, (o_lat, o_lon), (d_lat, d_lon))
                st.write("• Calculando rota alternativa (com interdição)...")
                coords_alt, dist_alt = calcular_rota_osm(
                    G_osm, (o_lat, o_lon), (d_lat, d_lon),
                    nos_remover=nos_remover,
                    arestas_remover=arestas_remover,
                )

                st.write("• Extraindo malha viária para visualização...")
                malha_geojson = _extrair_malha_geojson(G_osm)
                st.write(f"  ✓ Malha com {len(malha_geojson.get('features', []))} segmentos.")
                modo_usado = "OSM"
            else:
                # Modo simplificado: usa os 2 vizinhos mais próximos da OAE focal no grafo simplificado
                G_simp = construir_grafo_simplificado(df, k_vizinhos=3)
                vizinhos = list(G_simp.neighbors(oae_focal)) if oae_focal in G_simp else []
                if len(vizinhos) >= 2:
                    o_cod, d_cod = vizinhos[0], vizinhos[1]
                else:
                    # Fallback: usa duas OAEs distintas do dataset
                    todos = df["Código OAE"].astype(str).tolist()
                    o_cod = next((c for c in todos if c != oae_focal), oae_focal)
                    d_cod = next((c for c in todos if c not in (oae_focal, o_cod)), o_cod)
                o_lat, o_lon = obter_ponto(df, o_cod)
                d_lat, d_lon = obter_ponto(df, d_cod)
                st.write(f"• OD (modo simplificado): {o_cod} → {d_cod}")
                st.write("• Calculando rotas no grafo simplificado...")
                coords_orig, dist_orig = calcular_rota_simplificada(G_simp, o_cod, d_cod)
                coords_alt, dist_alt = calcular_rota_simplificada(
                    G_simp, o_cod, d_cod, set(map(str, interdicao))
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
        raio_km=(raio_usado_m / 1000.0) if raio_usado_m else None,
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
        tooltip=f"Ponto de simulação · lado A da {oae_focal}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(mapa)
    folium.Marker(
        [d_lat, d_lon],
        tooltip=f"Ponto de simulação · lado B da {oae_focal}",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
    ).add_to(mapa)
    st_folium(mapa, width=None, height=560, returned_objects=[])

    st.caption(
        f"**Análise de impacto local:** quanto uma viagem que **atravessa a "
        f"{oae_focal}** rodaria a mais caso ela esteja interditada. Origem e destino "
        f"são pontos sintéticos da via (não representam fluxos reais de O/D).  ·  "
        f"**Modo:** {modo_usado}  ·  "
        "🔵 Malha OSM  ·  🔴 Rota original (tracejada, passa pela OAE)  ·  "
        "🟢 Rota alternativa (proposta após interdição)."
    )

    return {
        "timestamp": datetime.now(),
        "oae_focal": str(oae_focal),
        "oae_focal_lat": float(oae_lat),
        "oae_focal_lon": float(oae_lon),
        "origem_lat": float(o_lat),
        "origem_lon": float(o_lon),
        "destino_lat": float(d_lat),
        "destino_lon": float(d_lon),
        # mantém origem/destino como strings legíveis (para PDF e tabela)
        "origem": f"({o_lat:.5f}, {o_lon:.5f})",
        "destino": f"({d_lat:.5f}, {d_lon:.5f})",
        "interdicao": [str(c) for c in interdicao],
        "dist_orig_m": float(dist_orig),
        "dist_alt_m": float(dist_alt) if tem_alt else 0.0,
        "tem_alt": bool(tem_alt),
        "modo": modo_usado,
        "raio_km": (raio_usado_m / 1000.0) if raio_usado_m else None,
    }


# ============================================================================
# MLP de priorização de manutenção (combina condição estrutural + impacto na rede)
# ============================================================================

@st.cache_resource(show_spinner="Treinando MLP de priorização...")
def _modelo_prioridade_mlp():
    """Treina um MLPRegressor para escore de prioridade de manutenção (0-100).

    Entradas: [Nota Geral (1-5), Impacto médio % (0-100)]
    Saída:    Prioridade (0-100), maior = mais urgente reparar

    Dados de treino: SINTÉTICOS, baseados em princípios de engenharia:
      - Condição estrutural pesa 60% (Nota baixa = manutenção urgente)
      - Impacto na malha pesa 40% (alto impacto = ponte é "gargalo crítico")
      - Função alvo combina lineamente com não-linearidade sigmoide para
        produzir curvas suaves nas zonas extremas (evita escores 0% ou 100% planos)

    Em produção, o MLP seria re-treinado com decisões reais de engenheiros de
    pontes (dados rotulados de prioridade histórica de manutenção).
    """
    from sklearn.neural_network import MLPRegressor
    import numpy as np

    rng = np.random.default_rng(42)
    n = 5000
    notas = rng.uniform(1, 5, n)
    impactos = rng.uniform(0, 100, n)

    # Ground truth: combinação ponderada com sigmoide suave
    score_struct = (6 - notas) / 5      # 0-1, maior = pior condição
    score_impacto = impactos / 100      # 0-1, maior = mais impacto
    combinado = 0.6 * score_struct + 0.4 * score_impacto  # 0-1
    # Sigmoide centrada em 0.5 com inclinação 5 → suaviza extremos
    prioridade = 100.0 / (1.0 + np.exp(-5 * (combinado - 0.5)))
    # Pequeno ruído para o MLP não memorizar exatamente
    prioridade = np.clip(prioridade + rng.normal(0, 2, n), 0, 100)

    X = np.column_stack([notas, impactos])
    y = prioridade

    mlp = MLPRegressor(
        hidden_layer_sizes=(16, 8),
        activation="relu",
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        tol=1e-4,
    )
    mlp.fit(X, y)
    return mlp


def _calcular_prioridade(nota: float, impacto_pct: float) -> float:
    """Retorna prioridade 0-100 para uma OAE usando o MLP treinado."""
    import numpy as np
    mlp = _modelo_prioridade_mlp()
    X = np.array([[nota, impacto_pct]])
    p = float(mlp.predict(X)[0])
    return max(0.0, min(100.0, p))


def _classifica_prioridade(score: float) -> str:
    if score >= 70:
        return "ALTA"
    if score >= 40:
        return "MEDIA"
    return "BAIXA"


def construir_ranking_prioridade(
    df: pd.DataFrame, simulacoes: list[dict]
) -> list[dict]:
    """Para cada OAE que apareceu nas simulações, calcula prioridade MLP.

    Retorna lista ordenada por prioridade descendente:
      [{codigo, nota, impacto_medio, aparicoes, prioridade, classe}, ...]
    """
    impactos: dict[str, list[float]] = {}
    for s in simulacoes:
        if not s["tem_alt"] or s["dist_orig_m"] <= 0 or s["dist_alt_m"] <= 0:
            continue
        imp_pct = (s["dist_alt_m"] - s["dist_orig_m"]) / s["dist_alt_m"] * 100.0
        for oae in s["interdicao"]:
            impactos.setdefault(oae, []).append(imp_pct)

    ranking = []
    for cod, vals in impactos.items():
        sel = df[df["Código OAE"].astype(str) == str(cod)]
        if sel.empty:
            continue
        try:
            nota = float(sel.iloc[0]["Nota Geral"])
        except (TypeError, ValueError, KeyError):
            continue
        impacto_medio = sum(vals) / len(vals)
        prioridade = _calcular_prioridade(nota, impacto_medio)
        ranking.append({
            "codigo": cod,
            "nota": nota,
            "impacto_medio": impacto_medio,
            "aparicoes": len(vals),
            "prioridade": prioridade,
            "classe": _classifica_prioridade(prioridade),
        })

    ranking.sort(key=lambda x: -x["prioridade"])
    return ranking


def gerar_pdf_relatorio(df: pd.DataFrame, simulacoes: list[dict]) -> bytes:
    """Gera um relatório PDF consolidando todas as simulações da sessão."""
    from fpdf import FPDF

    def _txt(s: object) -> str:
        # Garante que a string é codificável em Latin-1 (suporta PT-BR).
        # Substitui caracteres Unicode comuns por equivalentes Latin-1 ANTES
        # da codificação para não virarem '?'.
        s = str(s)
        substituicoes = {
            "—": "-",     # em-dash (—)
            "–": "-",     # en-dash (–)
            "‘": "'",     # smart quote left
            "’": "'",     # smart quote right
            "“": '"',     # smart double quote left
            "”": '"',     # smart double quote right
            "…": "...",   # ellipsis (…)
            " ": " ",     # non-breaking space
            "→": "->",    # right arrow (→)
            "←": "<-",    # left arrow (←)
            "·": "·",     # middle dot (mantém — está em Latin-1)
        }
        for orig, sub in substituicoes.items():
            s = s.replace(orig, sub)
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
    # Impacto % = (alt - orig) / alt * 100 (bounded 0-100%)
    incrementos_pct = [
        (s["dist_alt_m"] - s["dist_orig_m"]) / s["dist_alt_m"] * 100.0
        for s in simulacoes
        if s["tem_alt"] and s["dist_orig_m"] > 0 and s["dist_alt_m"] > 0
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
    pdf.cell(0, 5, _txt(f"- Aumento médio de distância: +{avg_inc:.2f} km (Impacto médio: {avg_pct:.1f}%)"), ln=True)
    pdf.cell(0, 5, _txt(f"- Aumento máximo observado: +{max_inc:.2f} km (Impacto máximo: {max_pct:.1f}%)"), ln=True)
    pdf.ln(5)

    # ----- Detalhamento por simulação -----
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(0, 224, 212)
    pdf.cell(72, 7, _txt(" Detalhamento das simulações"), fill=True, ln=True)
    pdf.ln(2)

    headers = ["#", "Hora", "OAE focal", "Lat / Lon", "Int", "Modo", "Orig(km)", "Alt(km)", "Imp.%", "Fator", "Raio"]
    widths  = [ 7,    12,     28,            33,           7,    10,      16,          16,        15,      13,      14]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(220, 230, 240)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _txt(h), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8.5)
    for i, s in enumerate(simulacoes, 1):
        hora = s["timestamp"].strftime("%H:%M:%S") if hasattr(s["timestamp"], "strftime") else str(s["timestamp"])
        impacto = "-"
        fator = "-"
        if s["tem_alt"] and s["dist_orig_m"] > 0 and s["dist_alt_m"] > 0:
            # Impacto = (alt - orig) / alt × 100  (0% a ~100%, sempre)
            impacto = f"{(s['dist_alt_m'] - s['dist_orig_m']) / s['dist_alt_m'] * 100:.1f}%"
            fator = f"{s['dist_alt_m'] / s['dist_orig_m']:.2f}x"
        elif not s["tem_alt"]:
            impacto = "sem rota"
        focal = s.get("oae_focal", "-")
        flat = s.get("oae_focal_lat")
        flon = s.get("oae_focal_lon")
        latlon = f"{flat:.5f}, {flon:.5f}" if flat is not None and flon is not None else "-"
        # Marca baseline curta com asterisco
        baseline_curta = bool(s["tem_alt"] and 0 < s["dist_orig_m"] < 1000)
        orig_str = f"{s['dist_orig_m']/1000:.2f}" if s["dist_orig_m"] else "-"
        if baseline_curta:
            orig_str = orig_str + "*"
        raio_str = f"{s['raio_km']:.1f}" if s.get("raio_km") else "-"
        row = [
            str(i),
            hora,
            focal[:16],
            latlon,
            str(len(s["interdicao"])),
            s["modo"],
            orig_str,
            f"{s['dist_alt_m']/1000:.2f}" if s["tem_alt"] else "-",
            impacto,
            fator,
            raio_str,
        ]
        for c, w in zip(row, widths):
            pdf.cell(w, 5.5, _txt(c), border=1, align="C")
        pdf.ln()

    # Aviso para baselines curtas (linhas marcadas com *)
    sims_curtas = [
        s for s in simulacoes
        if s["tem_alt"] and 0 < s["dist_orig_m"] < 1000
    ]
    if sims_curtas:
        pdf.ln(1.5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 60, 0)  # laranja escuro
        pdf.multi_cell(0, 3.5, _txt(
            f"* Baseline < 1 km em {len(sims_curtas)} simulacao(oes). A Var.% pode parecer "
            "extrema porque a rota original e muito curta — priorize o aumento absoluto e o "
            "Fator (x) para interpretar. Comum em OAEs cuja origem/destino sintetizados ficaram "
            "muito proximos da obra (pontes locais/curtas)."
        ))
        pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # ----- Priorização para Manutenção (MLP) -----
    ranking_mlp = construir_ranking_prioridade(df, simulacoes)

    if ranking_mlp:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(0, 224, 212)
        pdf.cell(98, 7, _txt(" Priorizacao para Manutencao (MLP)"), fill=True, ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.multi_cell(0, 4.2, _txt(
            "Escore 0-100 produzido por um Multi-Layer Perceptron (sklearn, topologia "
            "[2 -> 16 -> 8 -> 1]) treinado com dados sinteticos baseados em principios "
            "de engenharia: combina condicao estrutural (Nota Geral, peso 60%) e "
            "impacto na rede (Impacto medio nas simulacoes, peso 40%). Quanto maior "
            "o escore, mais urgente a manutencao. Classificacao: ALTA (>=70), MEDIA "
            "(40-69), BAIXA (<40)."
        ))
        pdf.ln(1.5)

        rank_headers = ["Pos", "Codigo OAE", "Nota", "Impacto med.", "Aparicoes", "Prioridade", "Classe"]
        rank_widths  = [10,    52,           14,     24,             18,           24,            18]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 240)
        for h, w in zip(rank_headers, rank_widths):
            pdf.cell(w, 6, _txt(h), border=1, align="C", fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)

        # Cores para classe ALTA/MEDIA/BAIXA
        cores_classe = {
            "ALTA":  (255, 220, 220),  # vermelho claro
            "MEDIA": (255, 240, 200),  # amarelo claro
            "BAIXA": (220, 240, 220),  # verde claro
        }

        for pos, item in enumerate(ranking_mlp[:10], 1):
            cor_fill = cores_classe.get(item["classe"], (255, 255, 255))
            row = [
                f"{pos}",
                item["codigo"],
                f"{item['nota']:.0f}",
                f"{item['impacto_medio']:.1f}%",
                str(item["aparicoes"]),
                f"{item['prioridade']:.1f}",
                item["classe"],
            ]
            # Pinta a célula 'Classe' com a cor correspondente
            for i, (c, w) in enumerate(zip(row, rank_widths)):
                if i == len(row) - 1:  # última coluna (Classe)
                    pdf.set_fill_color(*cor_fill)
                    pdf.cell(w, 5.5, _txt(c), border=1, align="C", fill=True)
                else:
                    pdf.cell(w, 5.5, _txt(c), border=1, align="C")
            pdf.ln()
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 3.2, _txt(
            "Nota: o MLP foi treinado com dados sinteticos. Em producao, recomenda-se "
            "re-treinar com decisoes historicas de manutencao tomadas por engenheiros "
            "de pontes (rotulos reais de prioridade)."
        ))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # ----- Metodologia -----
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(0, 5.5, _txt(" Metodologia"), fill=True, ln=True)
    pdf.ln(0.5)
    pdf.set_font("Helvetica", "", 8.5)
    # Line-height reduzido (3.8) e parágrafos com espaço menor para caber em 1 página
    pdf.multi_cell(0, 3.8, _txt(
        "Escopo: ANÁLISE DE IMPACTO LOCAL. Cada simulação responde à pergunta "
        "'quanto uma viagem que precisa atravessar a OAE focal rodaria a mais "
        "caso ela esteja interditada?'. Origem e destino são pontos sintéticos "
        "da própria via - não representam fluxos reais de O/D urbanos. "
        "Os resultados refletem a CRITICIDADE INDIVIDUAL da obra para a "
        "conectividade local, não o impacto sistêmico sobre viagens reais."
    ))
    pdf.ln(1.2)
    pdf.multi_cell(0, 3.8, _txt(
        "1) Rede viária obtida do OpenStreetMap num raio configurável em torno do "
        "centroide das OAEs interditadas, ou substituída por uma rede simplificada "
        "(vizinhos mais próximos) quando o OSM está indisponível."
    ))
    pdf.ln(0.8)
    pdf.multi_cell(0, 3.8, _txt(
        "2) Para cada OAE interditada, todas as arestas cuja geometria passa a menos "
        "de 100 m do ponto da OAE são removidas (bloqueio cirúrgico: captura pistas "
        "duplicadas e a estrutura da obra sem desconectar intersecções vizinhas)."
    ))
    pdf.ln(0.8)
    pdf.multi_cell(0, 3.8, _txt(
        "3) Para a OAE focal, origem e destino são derivados automaticamente como nós "
        "do grafo OSM em lados opostos da obra (30 m a 3 km), com ângulos "
        "preferencialmente opostos a partir da OAE."
    ))
    pdf.ln(0.8)
    pdf.multi_cell(0, 3.8, _txt(
        "4) Caminho mínimo calculado pelo algoritmo Dijkstra (NetworkX) com "
        "comprimento das vias como peso. Distâncias em metros (convertidas para km)."
    ))
    pdf.ln(0.8)
    pdf.multi_cell(0, 3.8, _txt(
        "5) Criticidade estimada empiricamente pelo aumento percentual médio de "
        "distância nos cenários em que a OAE foi interditada - indicador relativo "
        "de impacto local."
    ))
    pdf.ln(0.8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 3.8, _txt(
        "Nota sobre interdições múltiplas: quando uma simulação interdita N OAEs "
        "simultaneamente, o aumento de distância observado é atribuído a TODAS elas "
        "(divisão de crédito). Para ranqueamento puro de criticidade individual, "
        "rode uma simulação por OAE (uma interdição por vez)."
    ))
    pdf.set_font("Helvetica", "", 8.5)

    # ----- Rodapé (posicionado relativo ao conteúdo, não fixo no fim da página) -----
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(120, 120, 130)
    pdf.cell(
        0, 4,
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

    def _consolidar(fontes: list, label_origem: str) -> pd.DataFrame:
        """Carrega cada item, concatena e deduplica códigos."""
        partes = []
        for a in fontes:
            d = carregar_arquivo(a)
            if not d.empty:
                partes.append(d)
            else:
                nome = a.name if hasattr(a, "name") else str(a)
                st.sidebar.warning(f"⚠️ Sem registros em **{nome}** — ignorado.")
        if not partes:
            return pd.DataFrame()
        df = pd.concat(partes, ignore_index=True)
        if df["Código OAE"].duplicated().any():
            df["Código OAE"] = (
                df["Código OAE"].astype(str)
                + "_" + df.groupby("Código OAE").cumcount().astype(str)
            )
            df["Código OAE"] = df["Código OAE"].str.replace(r"_0$", "", regex=True)
        st.sidebar.success(
            f"✓ {label_origem}: {len(fontes)} arquivo(s) → **{len(df)} OAEs**"
        )
        return df

    arquivos_data_paths = opcoes.get("arquivos_data_paths") or []
    arquivos_upload = opcoes.get("arquivo") or []
    if not isinstance(arquivos_upload, list):
        arquivos_upload = [arquivos_upload]

    if arquivos_data_paths:
        df_novo = _consolidar(arquivos_data_paths, "Pasta data/")
    elif arquivos_upload:
        df_novo = _consolidar(arquivos_upload, "Upload")
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

    # ----- Enriquecimento automático (função NATIVA) -----
    # Roda após cada carga: aplica cache do session_state e, se houver OAEs
    # ainda sem Município/Rodovia, consulta o Nominatim/OSM (1 req/s).
    # Cada (lat, lon) é tentada apenas 1 vez por sessão.
    # IMPORTANTE: NÃO salvamos o df enriquecido em st.session_state["df"]!
    # Se salvasse, o df no session_state ficaria diferente do que o loader
    # produz (que vem sem enriquecimento), e a checagem df_novo.equals(df_atual)
    # acima dispararia rerun infinito. O cache do enriquecimento vive em
    # st.session_state["enrichment_cache"] e é reaplicado a cada render.
    df = enriquecer_geocodificacao_auto(df)

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
        f"Município/UF e Rodovia/Trecho são preenchidos automaticamente via OSM "
        f"quando ausentes nos KMZs originais (Nominatim · 1 consulta por OAE, "
        f"resultado em cache durante a sessão)."
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
                # Atualiza o contador na sidebar SEM aguardar próxima interação
                if opcoes.get("counter_slot") is not None:
                    _renderiza_contador_sim(opcoes["counter_slot"])
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
                "OAE focal": s.get("oae_focal", "—"),
                "Origem (lat,lon)": s.get("origem", ""),
                "Destino (lat,lon)": s.get("destino", ""),
                "Interditadas": len(s["interdicao"]),
                "Modo": s["modo"],
                "Dist. orig. (km)": round(s["dist_orig_m"] / 1000, 2) if s["dist_orig_m"] else None,
                "Dist. alt. (km)":  round(s["dist_alt_m"]  / 1000, 2) if s["tem_alt"] else None,
                "Impacto (%)": (
                    round((s["dist_alt_m"] - s["dist_orig_m"]) / s["dist_alt_m"] * 100, 1)
                    if s["tem_alt"] and s["dist_alt_m"] else None
                ),
                "Fator (×)": (
                    round(s["dist_alt_m"] / s["dist_orig_m"], 2)
                    if s["tem_alt"] and s["dist_orig_m"] else None
                ),
                "Raio (km)": (
                    round(s["raio_km"], 1) if s.get("raio_km") else None
                ),
                "Status": (
                    "❌ sem rota" if not s["tem_alt"]
                    else "⚠️ baseline curta" if 0 < s["dist_orig_m"] < 1000
                    else "✓"
                ),
            }
            for i, s in enumerate(simulacoes)
        ])
        st.dataframe(hist, use_container_width=True, hide_index=True, height=min(320, 50 + len(hist) * 36))

        # ----- Priorização MLP de Manutenção -----
        ranking_mlp = construir_ranking_prioridade(df, simulacoes)
        if ranking_mlp:
            st.markdown("")
            st.markdown("### 🛠️ Priorização de Manutenção (MLP)")
            st.caption(
                "Escore 0-100 produzido por um **Multi-Layer Perceptron** "
                "(`[2 → 16 → 8 → 1]`, scikit-learn) que combina **Nota Geral** "
                "(condição estrutural, peso 60%) e **Impacto médio na rede** "
                "(peso 40%). Quanto maior, mais urgente a manutenção. "
                "Classes: 🔴 ALTA (≥70) · 🟡 MÉDIA (40-69) · 🟢 BAIXA (<40)."
            )

            # Top 3 em destaque
            top3 = ranking_mlp[:3]
            cols_top = st.columns(len(top3))
            for col, item in zip(cols_top, top3):
                emoji_classe = {"ALTA": "🔴", "MEDIA": "🟡", "BAIXA": "🟢"}[item["classe"]]
                col.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="label">{emoji_classe} {item['classe']}</div>
                        <div class="value" style="font-size:1.05rem; line-height:1.2;">{item['codigo']}</div>
                        <div style="font-size:0.82rem; color:#A8B5CC; margin-top:0.3rem;">
                            Nota <b>{item['nota']:.0f}</b> · Impacto <b>{item['impacto_medio']:.1f}%</b><br>
                            Prioridade: <b style="color:#00E0D4;">{item['prioridade']:.1f}/100</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Tabela completa
            st.markdown("")
            df_rank = pd.DataFrame([
                {
                    "Pos.": i + 1,
                    "Código OAE": item["codigo"],
                    "Nota": item["nota"],
                    "Impacto médio (%)": round(item["impacto_medio"], 1),
                    "Aparições": item["aparicoes"],
                    "Prioridade (0-100)": round(item["prioridade"], 1),
                    "Classe": item["classe"],
                }
                for i, item in enumerate(ranking_mlp)
            ])
            st.dataframe(df_rank, use_container_width=True, hide_index=True)

            st.caption(
                "⚙️ **Defesa metodológica:** o MLP foi treinado com **dados sintéticos** "
                "baseados em princípios de engenharia (peso 60/40). Em produção, "
                "re-treinar com decisões reais de engenheiros de pontes (rótulos "
                "históricos de prioridade) substituindo os dados sintéticos."
            )

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

        # ----- Remover simulações específicas (sem rota, individuais) -----
        st.markdown("**Remover simulações do histórico**")
        sims_sem_rota_idx = [i for i, s in enumerate(simulacoes) if not s["tem_alt"]]
        c1, c2, c3 = st.columns([2, 3, 1])
        if c1.button(
            f"🗑️ Remover {len(sims_sem_rota_idx)} sem-rota",
            use_container_width=True,
            disabled=not sims_sem_rota_idx,
            help="Remove de uma vez todas as simulações que falharam (sem rota alternativa). "
                 "Útil pra limpar tentativas com raio muito pequeno antes de gerar o PDF.",
            key="btn_rm_sem_rota",
        ):
            st.session_state["simulacoes"] = [s for s in simulacoes if s["tem_alt"]]
            st.session_state["sim_count"] = len(st.session_state["simulacoes"])
            st.rerun()

        opcoes_remover = [
            f"#{i+1} · {s.get('oae_focal', '?')[:25]} · "
            f"{s['timestamp'].strftime('%H:%M:%S') if hasattr(s['timestamp'], 'strftime') else ''}"
            f"{' [SEM ROTA]' if not s['tem_alt'] else ''}"
            for i, s in enumerate(simulacoes)
        ]
        sim_a_remover = c2.selectbox(
            "Remover individual:",
            options=["— escolha uma simulação —"] + opcoes_remover,
            label_visibility="collapsed",
            key="sb_rm_individual",
        )
        if c3.button(
            "🗑️",
            disabled=(sim_a_remover == "— escolha uma simulação —"),
            help="Remove a simulação selecionada do histórico.",
            key="btn_rm_individual",
            use_container_width=True,
        ):
            idx = opcoes_remover.index(sim_a_remover)
            del st.session_state["simulacoes"][idx]
            st.session_state["sim_count"] = len(st.session_state["simulacoes"])
            st.rerun()

    # ----- Rodapé com autor e licença -----
    st.markdown(
        f"""
        <div class="app-footer">
            <b>{APP_TITLE}</b> &middot; {APP_MODULO} {APP_VERSAO}<br>
            Desenvolvido por <b>Luiz Araujo de Souza Junior</b>
            &middot; ET 261400 — Ciência de Dados e Aprendizado Profundo aplicados aos Transportes<br>
            Licença
            <a href="https://github.com/luizaraujoengkil-ux/simulador-resiliencia-oae/blob/main/LICENSE" target="_blank">MIT</a>
            &middot;
            <a href="https://github.com/luizaraujoengkil-ux/simulador-resiliencia-oae" target="_blank">código no GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
