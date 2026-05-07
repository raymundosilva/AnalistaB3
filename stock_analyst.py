#!/usr/bin/env python3
"""
=============================================================
  StockMind — Análise de Ações com IA
  Backend: Flask + Ollama (IA 100% local e gratuita)
=============================================================

ARQUITETURA GERAL:
  - Flask serve a página web (HTML/CSS/JS) e a API REST
  - O front-end (HTML embutido) é a interface de chat no navegador
  - Quando o usuário digita uma empresa, o JS faz um POST para /analyze
  - O backend extrai o ticker/nome do texto, monta o prompt e
    envia para o Ollama, que roda um modelo de IA localmente
  - A resposta da IA (JSON) é renderizada como card no chat

DEPENDÊNCIAS:
  pip install flask requests

COMO RODAR:
  1. Instale o Ollama: https://ollama.com
  2. Baixe um modelo:  ollama pull llama3.2
  3. Execute:          python stock_analyst.py
  4. Acesse:           http://localhost:5000
=============================================================
"""

# --- Importações ---
from flask import Flask, request, jsonify, render_template_string
import requests   # para fazer chamadas HTTP ao servidor Ollama
import json       # para serializar/desserializar JSON
import re         # para expressões regulares (extração de empresa do texto)
from datetime import datetime  # para timestamps (usado pelo front-end)

# --- Inicialização do app Flask ---
app = Flask(__name__)

# --- Configurações do Ollama ---
# URL padrão do servidor Ollama (roda localmente após "ollama serve")
OLLAMA_URL = "http://localhost:11434/api/generate"

# Modelo de IA a ser usado. Troque conforme o que você baixou:
#   llama3.2  → leve, ~2GB, bom para 8GB de RAM  (padrão)
#   mistral   → melhor qualidade, ~4GB, recomenda 16GB RAM
#   qwen2.5   → excelente custo-benefício, ~4GB
OLLAMA_MODEL = "llama3.2"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StockMind — Análise de Ações com IA</title>

<!-- Fontes do Google Fonts:
     DM Serif Display → títulos elegantes com serifa
     DM Mono         → valores numéricos e tickers (monoespaçada)
     Syne            → corpo do texto, navegação e labels -->
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=Syne:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
  /* Reset universal: remove margens e paddings padrão do navegador
     e usa border-box para que padding/border não aumentem o tamanho
     total dos elementos */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  /* ============================================================
     VARIÁVEIS DE DESIGN (CSS Custom Properties)
     Centralizam todas as cores e tamanhos usados no app.
     Para mudar o tema, basta alterar aqui.
  ============================================================ */
  :root {
    /* Fundos em tons de cinza escuro (tema dark) */
    --bg: #0a0b0f;         /* fundo principal da página */
    --bg2: #111318;        /* fundo da sidebar */
    --bg3: #181c24;        /* fundo dos cards de análise */
    --surface: #1e2330;    /* superfícies elevadas (bolhas, inputs) */
    --surface2: #252b3a;   /* superfície no estado hover */

    /* Bordas semitransparentes para separação sutil */
    --border: rgba(255,255,255,0.07);
    --border2: rgba(255,255,255,0.12);

    /* Hierarquia de texto: --text mais claro, --text3 mais apagado */
    --text: #e8eaf0;
    --text2: #8b92a8;
    --text3: #555c72;

    /* Azul de destaque para links, foco e elementos interativos */
    --accent: #4f9cf9;
    --accent2: #2563eb;

    /* Verde para COMPRA e indicadores positivos */
    --buy: #22c55e;
    --buy-dim: rgba(34,197,94,0.12);    /* versão transparente para fundos */

    /* Âmbar para NEUTRO e alertas de atenção */
    --neutral: #f59e0b;
    --neutral-dim: rgba(245,158,11,0.12);

    /* Vermelho para erros e indicadores negativos */
    --sell: #ef4444;
    --sell-dim: rgba(239,68,68,0.12);

    --gold: #e8c94a;       /* dourado reservado para detalhes especiais */

    /* Bordas arredondadas padronizadas */
    --radius: 14px;
    --radius-sm: 8px;
  }

  /* Layout base: coluna vertical ocupando toda a altura da janela */
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ============================================================
     HEADER — Barra superior fixa com logo e badge
  ============================================================ */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.25rem 2rem;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
    position: sticky;   /* fica fixo no topo ao rolar a página */
    top: 0;
    z-index: 100;       /* aparece acima de todo o conteúdo */
    backdrop-filter: blur(12px); /* desfoque glassmorphism atrás do header */
  }

  /* Grupo logo: ícone + nome do app lado a lado */
  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* Ícone quadrado com gradiente azul→roxo */
  .logo-icon {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, var(--accent) 0%, #7c3aed 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }

  /* Nome do app com serifa elegante */
  .logo-text {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: var(--text);
    letter-spacing: -0.02em;
  }

  /* "Mind" em azul de destaque */
  .logo-text span { color: var(--accent); }

  /* Badge pequeno no canto direito do header */
  .header-badge {
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    color: var(--text3);
    border: 1px solid var(--border2);
    padding: 4px 10px;
    border-radius: 20px;
    letter-spacing: 0.05em;
  }

  /* ============================================================
     LAYOUT PRINCIPAL — Sidebar + Área de chat lado a lado
  ============================================================ */
  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
    height: calc(100vh - 70px); /* ocupa o restante da tela abaixo do header */
  }

  /* ============================================================
     SIDEBAR — Painel lateral com atalhos de análise rápida
  ============================================================ */
  .sidebar {
    width: 280px;
    border-right: 1px solid var(--border);
    background: var(--bg2);
    padding: 1.5rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-y: auto; /* permite rolar se houver muitos atalhos */
  }

  /* Label de seção em maiúsculas e fonte mono */
  .sidebar-title {
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    color: var(--text3);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0 0.5rem;
    margin-bottom: 0.25rem;
  }

  /* Botão de atalho para cada empresa da sidebar */
  .quick-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.75rem 1rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* Efeito hover: fundo mais claro e leve deslocamento para direita */
  .quick-btn:hover {
    background: var(--surface2);
    border-color: var(--border2);
    transform: translateX(2px);
  }

  /* Badge do ticker (ex: PETR4) dentro do botão */
  .quick-btn .ticker {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: var(--accent);
    background: rgba(79,156,249,0.1);
    padding: 2px 7px;
    border-radius: 4px;
    min-width: 54px;
    text-align: center;
  }

  /* Nome da empresa ao lado do ticker */
  .quick-btn .company {
    color: var(--text2);
    font-size: 12px;
  }

  /* Separador horizontal entre grupos de botões */
  .divider {
    height: 1px;
    background: var(--border);
    margin: 0.5rem 0;
  }

  /* Aviso legal no rodapé da sidebar */
  .disclaimer {
    font-size: 10.5px;
    color: var(--text3);
    line-height: 1.6;
    padding: 0.75rem;
    background: var(--bg3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    margin-top: auto; /* empurra para o fundo da sidebar */
  }

  /* ============================================================
     ÁREA DE CHAT — Coluna principal com mensagens + input
  ============================================================ */
  .chat-area {
    flex: 1;             /* ocupa todo o espaço restante após a sidebar */
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Container rolável das mensagens */
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    scroll-behavior: smooth; /* animação suave ao rolar para o fim */
  }

  /* Scrollbar discreta no painel de mensagens */
  .messages::-webkit-scrollbar { width: 4px; }
  .messages::-webkit-scrollbar-track { background: transparent; }
  .messages::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  /* ============================================================
     TELA DE BOAS-VINDAS — Exibida quando não há mensagens ainda
  ============================================================ */
  .welcome {
    text-align: center;
    padding: 3rem 2rem;
    max-width: 560px;
    margin: 0 auto; /* centraliza horizontalmente */
  }

  /* Ícone animado com efeito de flutuação */
  .welcome-icon {
    font-size: 3.5rem;
    margin-bottom: 1.5rem;
    display: block;
    animation: float 3s ease-in-out infinite;
  }

  /* Animação de subir e descer suavemente */
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
  }

  .welcome h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: var(--text);
    margin-bottom: 0.75rem;
    letter-spacing: -0.03em;
  }

  .welcome p {
    color: var(--text2);
    font-size: 14px;
    line-height: 1.7;
    margin-bottom: 1.5rem;
  }

  /* Linha de chips clicáveis com sugestões de tickers */
  .welcome-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  /* Chip individual — clicável, dispara análise do ticker */
  .chip {
    background: var(--surface);
    border: 1px solid var(--border2);
    color: var(--text2);
    font-size: 12px;
    font-family: 'DM Mono', monospace;
    padding: 6px 14px;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s;
  }

  /* Hover do chip: borda e texto em azul */
  .chip:hover {
    background: var(--surface2);
    color: var(--accent);
    border-color: var(--accent);
  }

  /* ============================================================
     MENSAGENS DO CHAT — Bolhas do usuário e da IA
  ============================================================ */
  /* Estrutura base de cada mensagem: avatar + conteúdo */
  .msg {
    display: flex;
    gap: 1rem;
    max-width: 860px;
    width: 100%;
    animation: fadeUp 0.3s ease; /* aparece suavemente vindo de baixo */
  }

  /* Animação de entrada das mensagens */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Mensagem do usuário: alinhada à direita */
  .msg.user { flex-direction: row-reverse; align-self: flex-end; }

  /* Avatar circular com ícone ou letra */
  .msg-avatar {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0; /* não encolhe mesmo com conteúdo grande */
  }

  /* Avatar do usuário: fundo azul */
  .msg.user .msg-avatar { background: var(--accent2); color: white; font-size: 20px; font-weight: 600; }
  /* Avatar da IA: gradiente azul→roxo */
  .msg.ai .msg-avatar { background: linear-gradient(135deg, #4f9cf9, #7c3aed); }

  .msg-body { flex: 1; }
  /* Corpo da mensagem do usuário alinha o conteúdo à direita */
  .msg.user .msg-body { display: flex; justify-content: flex-end; }

  /* Bolha de mensagem genérica */
  .msg-bubble {
    padding: 0.875rem 1.125rem;
    border-radius: var(--radius);
    font-size: 14px;
    line-height: 1.65;
    max-width: 560px;
  }

  /* Bolha do usuário: fundo azul sólido, canto inferior direito reto */
  .msg.user .msg-bubble {
    background: var(--accent2);
    color: white;
    border-bottom-right-radius: 4px;
  }

  /* Bolha da IA: fundo escuro com borda, canto inferior esquerdo reto */
  .msg.ai .msg-bubble {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    border-bottom-left-radius: 4px;
    width: 100%;
    max-width: 100%;
  }

  /* ============================================================
     CARD DE ANÁLISE — Resultado detalhado da IA
  ============================================================ */
  .analysis-card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden; /* garante que bordas arredondadas sejam respeitadas */
    margin-top: 1rem;
  }

  /* Cabeçalho do card: ticker + nome da empresa + badge de recomendação */
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid var(--border);
  }

  .card-company { display: flex; flex-direction: column; gap: 4px; }

  /* Ticker em fonte monoespaçada grande (ex: PSSA3) */
  .card-ticker {
    font-family: 'DM Mono', monospace;
    font-size: 22px;
    font-weight: 500;
    color: var(--text);
    letter-spacing: 0.02em;
  }

  /* Nome completo da empresa menor e mais apagado */
  .card-name { font-size: 12px; color: var(--text2); }

  .recommendation-badge { display: flex; flex-direction: column; align-items: center; gap: 4px; }

  /* Pílula colorida com a recomendação: COMPRA (verde) ou NEUTRO (âmbar) */
  .rec-pill {
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 20px;
    border-radius: 24px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  /* Variações de cor conforme a recomendação */
  .rec-pill.buy     { background: var(--buy-dim);     color: var(--buy);     border: 1px solid rgba(34,197,94,0.3); }
  .rec-pill.neutral { background: var(--neutral-dim); color: var(--neutral); border: 1px solid rgba(245,158,11,0.3); }
  .rec-pill.sell    { background: var(--sell-dim);    color: var(--sell);    border: 1px solid rgba(239,68,68,0.3); }

  .rec-label { font-size: 10px; color: var(--text3); letter-spacing: 0.08em; text-transform: uppercase; font-family: 'DM Mono', monospace; }

  /* ============================================================
     BARRA DE SCORE — Indicador visual de atratividade (0–100)
  ============================================================ */
  .score-section {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid var(--border);
  }

  .score-title {
    font-size: 11px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-family: 'DM Mono', monospace;
    margin-bottom: 0.75rem;
  }

  /* Layout: barra + número do score ao lado */
  .score-bar-wrap { display: flex; align-items: center; gap: 12px; }

  /* Trilha cinza da barra */
  .score-bar-bg {
    flex: 1;
    height: 8px;
    background: var(--surface);
    border-radius: 4px;
    overflow: hidden;
  }

  /* Preenchimento colorido que cresce conforme o score (via width inline) */
  .score-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 1s ease; /* animação suave ao carregar */
  }

  /* Número do score à direita da barra */
  .score-value {
    font-family: 'DM Mono', monospace;
    font-size: 18px;
    font-weight: 500;
    min-width: 40px;
    text-align: right;
  }

  /* ============================================================
     GRID DE MÉTRICAS — 6 células com dados financeiros
  ============================================================ */
  /* Grade 3×2 com bordas entre as células usando gap de 1px + fundo */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--border); /* cria o efeito de borda entre células */
  }

  /* Cada célula da grade */
  .metric-cell { background: var(--bg3); padding: 1rem 1.25rem; }

  /* Label pequeno acima do valor */
  .metric-label {
    font-size: 10px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-family: 'DM Mono', monospace;
    margin-bottom: 5px;
  }

  /* Valor da métrica em fonte monoespaçada */
  .metric-value {
    font-family: 'DM Mono', monospace;
    font-size: 15px;
    font-weight: 500;
    color: var(--text);
  }

  /* Classes de cor aplicadas dinamicamente via JS conforme o valor */
  .metric-value.pos { color: var(--buy); }     /* positivo → verde */
  .metric-value.neg { color: var(--sell); }    /* negativo → vermelho */
  .metric-value.neu { color: var(--neutral); } /* neutro → âmbar */

  /* ============================================================
     SEÇÕES DE ANÁLISE — Resumo, catalisadores, riscos, valuation
  ============================================================ */
  .analysis-sections {
    padding: 1.25rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .section-block { display: flex; flex-direction: column; gap: 6px; }

  /* Cabeçalho de seção: ponto colorido + label em maiúsculas */
  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text2);
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  /* Ponto colorido que identifica o tipo de seção */
  .section-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .section-dot.green  { background: var(--buy); }
  .section-dot.red    { background: var(--sell); }
  .section-dot.yellow { background: var(--neutral); }
  .section-dot.blue   { background: var(--accent); }

  /* Texto da seção com indentação para alinhar com o ponto */
  .section-text {
    font-size: 13px;
    line-height: 1.7;
    color: var(--text2);
    padding-left: 14px;
  }

  /* Lista de catalisadores ou riscos */
  .catalysts { display: flex; flex-direction: column; gap: 4px; padding-left: 14px; }

  /* Cada item da lista com seta "→" como marcador */
  .catalyst-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    color: var(--text2);
    line-height: 1.6;
  }

  /* Marcador de seta em azul, posicionado antes do texto */
  .catalyst-item::before {
    content: "→";
    color: var(--accent);
    font-family: 'DM Mono', monospace;
    flex-shrink: 0;
    margin-top: 1px;
  }

  /* ============================================================
     RODAPÉ DO CARD — Timestamp + nível de confiança
  ============================================================ */
  .card-footer {
    padding: 0.875rem 1.5rem;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .footer-time { font-size: 10px; color: var(--text3); font-family: 'DM Mono', monospace; }

  .confidence-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text3);
    font-family: 'DM Mono', monospace;
  }

  /* ============================================================
     LOADING — Animação enquanto a IA processa a análise
  ============================================================ */
  .loading-bubble {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    border-bottom-left-radius: 4px;
    padding: 1rem 1.25rem;
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--text2);
    font-size: 13px;
  }

  /* Container dos 3 pontinhos animados */
  .loading-dots { display: flex; gap: 4px; }

  /* Cada ponto pulsa em sequência com delay diferente */
  .loading-dots span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
  }

  /* Delays escalonados para efeito cascata */
  .loading-dots span:nth-child(2) { animation-delay: 0.2s; }
  .loading-dots span:nth-child(3) { animation-delay: 0.4s; }

  /* Ponto diminui e some, depois volta com tamanho original */
  @keyframes pulse {
    0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
    30% { opacity: 1; transform: scale(1); }
  }

  /* ============================================================
     ÁREA DE INPUT — Campo de texto + botão enviar
  ============================================================ */
  .input-area {
    padding: 1.25rem 2rem;
    border-top: 1px solid var(--border);
    background: var(--bg);
  }

  /* Wrapper do input: fundo escuro, borda que muda ao focar */
  .input-wrap {
    display: flex;
    gap: 10px;
    align-items: flex-end;
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 0.75rem 1rem;
    transition: border-color 0.2s;
  }

  /* Borda azul ao focar qualquer filho (o textarea) */
  .input-wrap:focus-within { border-color: var(--accent); }

  /* Textarea expansível (sem borda, sem outline nativo) */
  #chatInput {
    flex: 1;
    background: none;
    border: none;
    outline: none;
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 14px;
    resize: none;         /* desativa resize manual pelo usuário */
    min-height: 24px;
    max-height: 120px;    /* limite máximo antes de rolar internamente */
    line-height: 1.5;
  }

  #chatInput::placeholder { color: var(--text3); }

  /* Botão de enviar: quadrado arredondado com ícone de avião */
  .send-btn {
    width: 36px;
    height: 36px;
    border-radius: 9px;
    border: none;
    background: var(--accent2);
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    flex-shrink: 0;
  }

  /* Hover: cor mais clara e leve aumento de tamanho */
  .send-btn:hover { background: var(--accent); transform: scale(1.05); }
  /* Desabilitado durante loading: cinza e sem cursor */
  .send-btn:disabled { background: var(--surface2); cursor: not-allowed; transform: none; }

  /* Dica abaixo do input */
  .input-hint {
    font-size: 11px;
    color: var(--text3);
    text-align: center;
    margin-top: 8px;
    font-family: 'DM Mono', monospace;
  }

  /* Bolha de erro exibida quando a IA ou servidor retorna problema */
  .error-bubble {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: var(--radius);
    border-bottom-left-radius: 4px;
    padding: 0.875rem 1.125rem;
    font-size: 13px;
    color: #fca5a5;
    line-height: 1.6;
  }
</style>
</head>
<body>

<!-- ============================================================
     HEADER — Logo + badge fixos no topo da página
============================================================ -->
<header>
  <div class="logo">
    <div class="logo-icon">📊</div>
    <div class="logo-text">Analista<span>B3</span></div>
  </div>
  <div class="header-badge">AI · POWERED · ANALYSIS</div>
</header>

<!-- ============================================================
     LAYOUT PRINCIPAL — Sidebar (esquerda) + Chat (direita)
============================================================ -->
<div class="main">

  <!-- SIDEBAR: atalhos para análises rápidas de empresas populares -->
  <aside class="sidebar">
    <div class="sidebar-title">Análises rápidas</div>

    <!-- Cada botão chama quickAnalyze(ticker) ao ser clicado -->
    <button class="quick-btn" onclick="quickAnalyze('PETR4')">
      <span class="ticker">PETR4</span>
      <span class="company">Petrobras</span>
    </button>
    <button class="quick-btn" onclick="quickAnalyze('VALE3')">
      <span class="ticker">VALE3</span>
      <span class="company">Vale</span>
    </button>
    <button class="quick-btn" onclick="quickAnalyze('ITUB4')">
      <span class="ticker">ITUB4</span>
      <span class="company">Itaú Unibanco</span>
    </button>
    <button class="quick-btn" onclick="quickAnalyze('PSSA3')">
      <span class="ticker">PSSA3</span>
      <span class="company">Porto Seguro</span>
    </button>
    <button class="quick-btn" onclick="quickAnalyze('MGLU3')">
      <span class="ticker">MGLU3</span>
      <span class="company">Magazine Luiza</span>
    </button>
     <button class="quick-btn" onclick="quickAnalyze('BPAC3')">
      <span class="ticker">BPAC3</span>
      <span class="company">BTG Pactual</span>
    </button>

    <!-- Separador visual entre empresas brasileiras e internacionais -->
    <div class="divider"></div>

    <button class="quick-btn" onclick="quickAnalyze('Apple')">
      <span class="ticker">AAPL</span>
      <span class="company">Apple Inc.</span>
    </button>
    <button class="quick-btn" onclick="quickAnalyze('Microsoft')">
      <span class="ticker">MSFT</span>
      <span class="company">Microsoft</span>
    </button>
    <button class="quick-btn" onclick="quickAnalyze('NVIDIA')">
      <span class="ticker">NVDA</span>
      <span class="company">NVIDIA Corp.</span>
    </button>

    <!-- Aviso legal obrigatório em apps de análise financeira -->
    <div class="disclaimer">
      ⚠️ As análises são geradas por IA com base em dados históricos e conhecimento geral. Não constituem recomendação de investimento. Consulte um assessor antes de investir.
    </div>
  </aside>

  <!-- ÁREA DE CHAT: onde as mensagens e análises aparecem -->
  <div class="chat-area">

    <!-- Container de mensagens — rolável, cresce de cima para baixo -->
    <div class="messages" id="messages">

      <!-- Tela de boas-vindas exibida antes da primeira análise -->
      <div class="welcome">
        <span class="welcome-icon">🧠</span>
        <h1>Análise de ações com IA</h1>
        <p>Digite o ticker ou nome de qualquer empresa para receber uma análise fundamentalista e técnica com recomendação de compra ou neutro.</p>

        <!-- Chips de sugestão: clicar dispara a análise direto -->
        <div class="welcome-chips">
          <span class="chip" onclick="quickAnalyze('PSSA3')">PSSA3</span>
          <span class="chip" onclick="quickAnalyze('PETR4')">PETR4</span>
          <span class="chip" onclick="quickAnalyze('Apple')">Apple</span>
          <span class="chip" onclick="quickAnalyze('VALE3')">VALE3</span>
          <span class="chip" onclick="quickAnalyze('Tesla')">Tesla</span>
          <span class="chip" onclick="quickAnalyze('ITUB4')">ITUB4</span>
        </div>
      </div>
    </div>

    <!-- ============================================================
         ÁREA DE INPUT — Onde o usuário digita a empresa
    ============================================================ -->
    <div class="input-area">
      <div class="input-wrap">
        <!-- Textarea expansível:
             - onkeydown: captura Enter (enviar) e Shift+Enter (nova linha)
             - oninput: ajusta altura automaticamente conforme o texto cresce -->
        <textarea
          id="chatInput"
          placeholder="Digite o ticker ou nome da empresa... ex: PSSA3, Apple, PETR4"
          rows="1"
          onkeydown="handleKey(event)"
          oninput="autoResize(this)"
        ></textarea>

        <!-- Botão de enviar com ícone SVG de avião de papel -->
        <button class="send-btn" id="sendBtn" onclick="sendMessage()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
      <!-- Dica de atalho de teclado para o usuário -->
      <div class="input-hint">Enter para enviar · Shift+Enter para nova linha</div>
    </div>
  </div>

</div>

<!-- ============================================================
     JAVASCRIPT — Toda a lógica do front-end
============================================================ -->
<script>
// ─── Referências aos elementos do DOM ───────────────────────────────────────
const messagesEl = document.getElementById('messages'); // container de mensagens
const input      = document.getElementById('chatInput'); // campo de texto
const sendBtn    = document.getElementById('sendBtn');   // botão enviar

// Flag para evitar múltiplos envios simultâneos enquanto a IA processa
let isLoading = false;

// ─── autoResize ─────────────────────────────────────────────────────────────
// Ajusta a altura do textarea conforme o usuário digita,
// respeitando o máximo de 120px definido no CSS.
function autoResize(el) {
  el.style.height = 'auto';                                  // reseta altura
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';  // aplica nova altura
}

// ─── handleKey ──────────────────────────────────────────────────────────────
// Captura o evento de teclado no textarea:
// - Enter sozinho → envia a mensagem
// - Shift+Enter   → quebra de linha (comportamento padrão)
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault(); // impede quebra de linha no Enter simples
    sendMessage();
  }
}

// ─── quickAnalyze ───────────────────────────────────────────────────────────
// Chamado pelos botões da sidebar e chips de sugestão.
// Preenche o input com o ticker e dispara o envio automaticamente.
function quickAnalyze(ticker) {
  input.value = ticker;
  sendMessage();
}

// ─── scrollBottom ───────────────────────────────────────────────────────────
// Rola o painel de mensagens até o fim para mostrar a última mensagem.
function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ─── addUserMsg ─────────────────────────────────────────────────────────────
// Cria e exibe a bolha de mensagem do usuário no chat.
function addUserMsg(text) {
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-body">
      <div class="msg-bubble">${escapeHtml(text)}</div>
    </div>
  `;
  messagesEl.appendChild(el);
  scrollBottom();
}

// ─── addLoadingMsg ──────────────────────────────────────────────────────────
// Exibe a bolha de "carregando" com os 3 pontinhos animados
// enquanto aguarda a resposta da IA.
function addLoadingMsg() {
  const el = document.createElement('div');
  el.className = 'msg ai';
  el.id = 'loadingMsg'; // id fixo para poder remover depois
  el.innerHTML = `
    <div class="msg-avatar">🧠</div>
    <div class="msg-body">
      <div class="loading-bubble">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
        <span>Analisando ativo e mercado...</span>
      </div>
    </div>
  `;
  messagesEl.appendChild(el);
  scrollBottom();
  return el;
}

// ─── removeLoading ──────────────────────────────────────────────────────────
// Remove a bolha de loading após receber a resposta da IA.
function removeLoading() {
  const el = document.getElementById('loadingMsg');
  if (el) el.remove();
}

// ─── addErrorMsg ────────────────────────────────────────────────────────────
// Exibe uma bolha vermelha de erro no chat.
function addErrorMsg(msg) {
  const el = document.createElement('div');
  el.className = 'msg ai';
  el.innerHTML = `
    <div class="msg-avatar">🧠</div>
    <div class="msg-body">
      <div class="error-bubble">⚠️ ${escapeHtml(msg)}</div>
    </div>
  `;
  messagesEl.appendChild(el);
  scrollBottom();
}

// ─── escapeHtml ─────────────────────────────────────────────────────────────
// Escapa caracteres especiais HTML para evitar XSS ao inserir
// texto externo (do usuário ou da IA) diretamente no DOM.
function escapeHtml(t) {
  return t
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── getScoreColor ──────────────────────────────────────────────────────────
// Retorna a cor CSS correspondente ao score de atratividade:
// >= 70 → verde (atrativo), >= 40 → âmbar (moderado), < 40 → vermelho (fraco)
function getScoreColor(score) {
  if (score >= 70) return 'var(--buy)';
  if (score >= 40) return 'var(--neutral)';
  return 'var(--sell)';
}

// ─── renderAnalysis ─────────────────────────────────────────────────────────
// Recebe o objeto JSON retornado pela IA e gera o HTML do card
// completo com todas as seções: header, score, métricas, análise.
function renderAnalysis(data) {
  // Determina a recomendação e sua classe CSS de cor
  const rec      = (data.recommendation || 'NEUTRO').toUpperCase();
  const recClass = rec === 'COMPRA' ? 'buy' : rec === 'VENDA' ? 'sell' : 'neutral';

  // Score e sua cor correspondente
  const score      = data.score || 50;
  const scoreColor = getScoreColor(score);

  // Gera os itens HTML de catalisadores e riscos (podem ser vazios)
  const catalysts = (data.catalysts || []).map(c =>
    `<div class="catalyst-item">${escapeHtml(c)}</div>`
  ).join('');

  const risks = (data.risks || []).map(r =>
    `<div class="catalyst-item">${escapeHtml(r)}</div>`
  ).join('');

  const metrics = data.metrics || {};

  // Determina a classe de cor de um valor de métrica:
  // "+" ou "positiv" → verde, "-" ou "negat" → vermelho, senão neutro
  function metricClass(val) {
    if (!val || val === 'N/D') return '';
    if (val.toString().startsWith('+') || val.toString().includes('positiv')) return 'pos';
    if (val.toString().startsWith('-') || val.toString().includes('negat')) return 'neg';
    return '';
  }

  // Timestamp formatado em pt-BR para o rodapé do card
  const now = new Date().toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

  // Retorna o HTML completo do card como string
  return `
    <div class="analysis-card">

      <!-- Cabeçalho: ticker + nome + badge de recomendação -->
      <div class="card-header">
        <div class="card-company">
          <div class="card-ticker">${escapeHtml(data.ticker || '')}</div>
          <div class="card-name">${escapeHtml(data.company_name || '')}</div>
        </div>
        <div class="recommendation-badge">
          <div class="rec-label">Recomendação</div>
          <div class="rec-pill ${recClass}">${rec}</div>
        </div>
      </div>

      <!-- Barra de score: largura dinâmica via style inline -->
      <div class="score-section">
        <div class="score-title">Score de atratividade</div>
        <div class="score-bar-wrap">
          <div class="score-bar-bg">
            <div class="score-bar-fill" style="width: ${score}%; background: ${scoreColor};"></div>
          </div>
          <div class="score-value" style="color: ${scoreColor};">${score}</div>
        </div>
      </div>

      <!-- Grade 3×2 com métricas financeiras da empresa -->
      <div class="metrics-grid">
        <div class="metric-cell">
          <div class="metric-label">Setor</div>
          <div class="metric-value">${escapeHtml(metrics.sector || 'N/D')}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-label">P/L Estimado</div>
          <div class="metric-value ${metricClass(metrics.pe)}">${escapeHtml(metrics.pe || 'N/D')}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-label">Market Cap</div>
          <div class="metric-value">${escapeHtml(metrics.market_cap || 'N/D')}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-label">Dividend Yield</div>
          <div class="metric-value pos">${escapeHtml(metrics.dividend_yield || 'N/D')}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-label">Tendência</div>
          <div class="metric-value ${metricClass(metrics.trend)}">${escapeHtml(metrics.trend || 'N/D')}</div>
        </div>
        <div class="metric-cell">
          <div class="metric-label">Bolsa</div>
          <div class="metric-value">${escapeHtml(metrics.exchange || 'N/D')}</div>
        </div>
      </div>

      <!-- Seções textuais: resumo, catalisadores, riscos, valuation -->
      <div class="analysis-sections">

        <!-- Resumo geral da empresa -->
        <div class="section-block">
          <div class="section-header">
            <div class="section-dot blue"></div>
            Resumo
          </div>
          <div class="section-text">${escapeHtml(data.summary || '')}</div>
        </div>

        <!-- Catalisadores (renderizado apenas se existirem itens) -->
        ${catalysts ? `
        <div class="section-block">
          <div class="section-header">
            <div class="section-dot green"></div>
            Catalisadores positivos
          </div>
          <div class="catalysts">${catalysts}</div>
        </div>
        ` : ''}

        <!-- Riscos (renderizado apenas se existirem itens) -->
        ${risks ? `
        <div class="section-block">
          <div class="section-header">
            <div class="section-dot red"></div>
            Principais riscos
          </div>
          <div class="catalysts">${risks}</div>
        </div>
        ` : ''}

        <!-- Valuation (renderizado apenas se a IA retornou o campo) -->
        ${data.valuation ? `
        <div class="section-block">
          <div class="section-header">
            <div class="section-dot yellow"></div>
            Valuation
          </div>
          <div class="section-text">${escapeHtml(data.valuation)}</div>
        </div>
        ` : ''}
      </div>

      <!-- Rodapé: data/hora de geração + nível de confiança -->
      <div class="card-footer">
        <div class="footer-time">Gerado em ${now}</div>
        <div class="confidence-wrap">
          Confiança: ${data.confidence || 'Moderada'}
        </div>
      </div>
    </div>
  `;
}

// ─── addAIMsg ───────────────────────────────────────────────────────────────
// Exibe a resposta da IA no chat:
// - Se vier com "error", mostra bolha vermelha de erro
// - Caso contrário, mostra texto de introdução + card de análise
function addAIMsg(data) {
  const el = document.createElement('div');
  el.className = 'msg ai';

  let innerContent = '';
  if (data.error) {
    // A IA ou o backend retornou um erro — exibe em vermelho
    innerContent = `<div class="error-bubble">⚠️ ${escapeHtml(data.error)}</div>`;
  } else {
    // Introdução em bolha normal + card completo de análise
    const intro = `<div class="msg-bubble" style="margin-bottom: 0.75rem;">${escapeHtml(data.intro || `Aqui está a análise de ${data.ticker || 'este ativo'}:`)}</div>`;
    innerContent = intro + renderAnalysis(data);
  }

  el.innerHTML = `
    <div class="msg-avatar">🧠</div>
    <div class="msg-body">${innerContent}</div>
  `;
  messagesEl.appendChild(el);
  scrollBottom();
}

// ─── sendMessage ────────────────────────────────────────────────────────────
// Função principal disparada ao clicar em Enviar ou pressionar Enter.
// Fluxo completo:
//   1. Valida input e bloqueia novos envios (isLoading)
//   2. Exibe a mensagem do usuário no chat
//   3. Exibe bolha de loading
//   4. Faz POST para /analyze com o texto digitado
//   5. Remove loading e exibe o resultado (ou erro)
//   6. Reabilita o campo e recoloca o foco
async function sendMessage() {
  if (isLoading) return; // ignora clique duplo durante processamento

  const text = input.value.trim();
  if (!text) return; // ignora envio com campo vazio

  // Bloqueia novos envios e desabilita o botão visualmente
  isLoading = true;
  sendBtn.disabled = true;

  // Limpa o campo e reseta sua altura
  input.value = '';
  input.style.height = 'auto';

  // Exibe a mensagem do usuário e o indicador de loading
  addUserMsg(text);
  addLoadingMsg();

  try {
    // Envia o texto para o backend Flask via fetch (requisição assíncrona)
    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text }) // { query: "analise a Vale" }
    });

    // Converte a resposta para objeto JS e renderiza no chat
    const data = await resp.json();
    removeLoading();
    addAIMsg(data);

  } catch (e) {
    // Erro de rede (servidor offline, timeout etc.)
    removeLoading();
    addErrorMsg('Erro ao conectar com o servidor. Tente novamente.');

  } finally {
    // Sempre reabilita o campo ao final, independente do resultado
    isLoading = false;
    sendBtn.disabled = false;
    input.focus(); // devolve foco ao input para próxima digitação
  }
}
</script>

</body>
</html>"""

SYSTEM_PROMPT = """Você é um analista financeiro sênior. Sua tarefa é analisar EXATAMENTE a empresa ou ticker solicitado.

=== REGRA CRÍTICA DE IDENTIDADE ===
Você DEVE identificar corretamente a empresa antes de qualquer análise.
Exemplos obrigatórios de mapeamento:
- PSSA3 = Porto Seguro S.A. (seguradora brasileira, setor: Seguros)
- PETR4 = Petrobras (petróleo, setor: Energia)
- PETR3 = Petrobras (petróleo, setor: Energia)
- ITUB4 = Itaú Unibanco (banco, setor: Financeiro)
- BBDC4 = Bradesco (banco, setor: Financeiro)
- VALE3 = Vale S.A. (mineração, setor: Mineração)
- MGLU3 = Magazine Luiza (varejo, setor: Varejo)
- WEGE3 = WEG S.A. (industrial, setor: Indústria)
- RENT3 = Localiza (aluguel de carros, setor: Mobilidade)
- BBAS3 = Banco do Brasil (banco público, setor: Financeiro)
- RADL3 = Raia Drogasil (farmácias, setor: Saúde)
- LREN3 = Lojas Renner (moda, setor: Varejo)
- HAPV3 = Hapvida (saúde, setor: Saúde)
- SUZB3 = Suzano (papel e celulose, setor: Papel/Celulose)
- GGBR4 = Gerdau (siderurgia, setor: Siderurgia)
- AAPL  = Apple Inc. (tecnologia, setor: Tecnologia)
- MSFT  = Microsoft (tecnologia, setor: Tecnologia)
- NVDA  = NVIDIA (semicondutores, setor: Tecnologia)
- TSLA  = Tesla (elétricos, setor: Automotivo/Energia)
- AMZN  = Amazon (e-commerce/cloud, setor: Tecnologia)
- GOOGL = Alphabet/Google (tecnologia, setor: Tecnologia)

Se o ticker não estiver na lista acima, identifique pelo nome da empresa e use seu conhecimento.
NUNCA confunda empresas. NUNCA use dados de uma empresa para outra.
Se não conseguir identificar, retorne: {"error": "Empresa não identificada. Tente o nome completo."}

=== FORMATO DE RESPOSTA ===
Retorne APENAS um JSON válido, sem markdown, sem texto antes ou depois, sem ```json```.

{
  "ticker": "TICKER_CORRETO",
  "company_name": "Nome oficial completo da empresa",
  "intro": "Uma frase apresentando a empresa e o contexto da análise",
  "recommendation": "COMPRA ou NEUTRO",
  "score": <inteiro de 0 a 100>,
  "confidence": "Alta ou Moderada ou Baixa",
  "summary": "2 a 3 frases sobre o perfil real da empresa e sua situação atual no mercado",
  "catalysts": [
    "Catalisador positivo específico desta empresa",
    "Catalisador positivo específico desta empresa",
    "Catalisador positivo específico desta empresa"
  ],
  "risks": [
    "Risco específico desta empresa",
    "Risco específico desta empresa",
    "Risco específico desta empresa"
  ],
  "valuation": "Comentário sobre valuation desta empresa específica",
  "metrics": {
    "sector": "Setor correto desta empresa",
    "pe": "P/L estimado desta empresa",
    "market_cap": "Market cap aproximado desta empresa",
    "dividend_yield": "DY estimado desta empresa ou N/D",
    "trend": "Alta ou Lateral ou Queda",
    "exchange": "B3 ou NYSE ou NASDAQ"
  }
}

=== REGRAS FINAIS ===
- COMPRA: score >= 60, fundamentos positivos predominam
- NEUTRO: score < 60, cautela recomendada
- Nunca use VENDA
- Use apenas dados reais desta empresa específica
- Se não souber um valor exato, estime com base no setor e histórico
- Retorne SOMENTE o JSON"""


# =============================================================
# ROTA PRINCIPAL — Serve a interface web (HTML/CSS/JS)
# =============================================================
@app.route('/')
def index():
    """
    Rota GET /
    Renderiza e retorna a página HTML completa do chat.
    O HTML_TEMPLATE contém toda a interface: sidebar, área de chat,
    campo de input e a lógica JavaScript de comunicação com o backend.
    """
    return render_template_string(HTML_TEMPLATE)


# =============================================================
# FUNÇÃO AUXILIAR — Extrai empresa/ticker do texto livre
# =============================================================
def extract_company(user_input):
    """
    Interpreta o texto digitado pelo usuário e extrai apenas
    o nome ou ticker da empresa, ignorando frases como
    'analise a empresa', 'faça uma análise de', etc.

    Exemplos:
      'PSSA3'                        → 'PSSA3'
      'analise a empresa Vale'       → 'Vale'
      'faça uma análise da Petrobras'→ 'Petrobras'
      'quero ver o ITUB4'            → 'ITUB4'

    Estratégia em 3 etapas:
      1. Ticker curto → retorna diretamente (ex: 'VALE3')
      2. Regex para padrões comuns em português
      3. Fallback: remove palavras-chave e retorna o restante
    """

    stripped = user_input.strip()

    # --- Etapa 1: Ticker direto ---
    # Se o texto tem até 6 caracteres e sem espaço, é provavelmente
    # um ticker puro (ex: PSSA3, AAPL, VALE3). Retorna em maiúsculas.
    if len(stripped) <= 6 and ' ' not in stripped:
        return stripped.upper()

    # --- Etapa 2: Regex com padrões de linguagem natural ---
    # Cada padrão cobre uma forma comum de o usuário pedir a análise.
    # O grupo de captura (entre parênteses) extrai o nome da empresa.
    patterns = [
        # "analise a empresa Cirela" / "analise Vale"
        r'(?:analise|analisar|analisa)\s+(?:a\s+)?(?:empresa|acao|ativo|papel|stock)?\s*([A-Za-z0-9][\w\s\.&]{1,40}?)(?:\s+para\s+mim|\s+por\s+favor|[,.]|$)',

        # "empresa Magazine Luiza" / "ativo PETR4"
        r'(?:empresa|acao|ativo|papel|stock)\s+([A-Za-z0-9][\w\s\.&]{1,40}?)(?:\s+para\s+mim|\s+por\s+favor|[,.]|$)',

        # "da empresa Vale" / "sobre a Petrobras"
        r'(?:da|do|de|sobre|para)\s+(?:a\s+empresa\s+|o\s+)?([A-Z][A-Za-z0-9][\w\s\.&]{1,30}?)(?:\s+para\s+mim|\s+por\s+favor|[,.]|$)',

        # "quero analisar a Apple" / "preciso de análise da Tesla"
        r'(?:faca|faz|quero|preciso)[^a-zA-Z]*(?:analise|analisar)[^a-zA-Z]*([A-Za-z0-9][\w\s\.&]{1,40}?)(?:\s+para\s+mim|\s+por\s+favor|[,.]|$)',
    ]

    # Palavras genéricas que não são nomes de empresa — usadas para
    # descartar falsos positivos nos grupos de captura
    ignore_words = {
        'mim', 'favor', 'por', 'me', 'uma', 'um',
        'essa', 'este', 'esta', 'acao', 'empresa'
    }

    for pattern in patterns:
        match = re.search(pattern, stripped, re.IGNORECASE)
        if match:
            found = match.group(1).strip()
            # Descarta se for uma palavra genérica ou muito curta
            if found.lower() not in ignore_words and len(found) > 1:
                return found.strip()

    # --- Etapa 3: Fallback por remoção de palavras-chave ---
    # Remove todos os termos comuns de solicitação e retorna
    # o que sobrar, que deve ser o nome da empresa.
    clean = re.sub(
        r'(?i)\b(por favor|pfv|pf|faça|faca|faz|uma|analise|analisar|analisa|'
        r'da empresa|do ativo|da acao|do papel|quero|preciso|gostaria|pode|'
        r'ver|mostrar|fazer|realizar|analise|de|da|do|sobre|para|a|o|me)\b',
        ' ', stripped
    )
    # Remove espaços duplos gerados pela remoção acima
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Retorna o texto limpo, ou o original se tudo foi removido
    return clean if clean else stripped


# =============================================================
# ROTA DE ANÁLISE — Recebe o input e consulta a IA
# =============================================================
@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Rota POST /analyze
    Recebe JSON com o campo 'query' (texto digitado pelo usuário),
    extrai o nome/ticker da empresa, monta o prompt, envia ao Ollama
    e retorna o JSON de análise para o front-end renderizar.

    Fluxo:
      1. Recebe { "query": "analise a Vale" }
      2. Extrai empresa → "Vale"
      3. Monta prompt com SYSTEM_PROMPT + empresa identificada
      4. Envia ao Ollama via HTTP POST
      5. Extrai o JSON da resposta da IA
      6. Retorna o JSON para o front-end

    Erros tratados:
      - Input vazio
      - Ollama offline (ConnectionError)
      - IA retornou resposta fora do formato JSON esperado
      - Qualquer outro erro inesperado
    """

    # Lê o corpo da requisição JSON enviado pelo front-end
    data = request.json
    raw_query = (data.get('query') or '').strip()

    # Valida se o usuário enviou algum texto
    if not raw_query:
        return jsonify({"error": "Por favor, informe o nome ou ticker da ação."})

    # Extrai o nome/ticker real do texto livre do usuário
    # Ex: "faça uma análise da Petrobras" → "Petrobras"
    query = extract_company(raw_query)

    try:
        # --- Monta o prompt final ---
        # Combina o SYSTEM_PROMPT (instruções da IA) com a solicitação
        # específica do usuário, incluindo o texto original e o ticker
        # extraído para dar mais contexto ao modelo.
        prompt = f"""{SYSTEM_PROMPT}

=== SOLICITAÇÃO ===
O usuário digitou: "{raw_query}"
Empresa ou ticker identificado: {query.upper()}
Analise SOMENTE a empresa "{query}" e retorne o JSON."""

        # --- Envia a requisição ao Ollama ---
        # O Ollama expõe uma API REST local na porta 11434.
        # "stream: False" faz o Ollama aguardar a resposta completa
        # antes de retornar (ao invés de streaming token a token).
        # "temperature: 0.2" deixa a IA mais determinística/precisa.
        # "top_p: 0.9" limita a aleatoriedade na escolha de tokens.
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,   # 0 = determinístico, 1 = criativo
                "num_predict": 1500,  # limite máximo de tokens na resposta
                "top_p": 0.9          # nucleus sampling para qualidade
            }
        }, timeout=120)  # timeout de 2 min para modelos mais lentos

        # Verifica se o Ollama retornou sucesso (HTTP 200)
        if response.status_code != 200:
            return jsonify({
                "error": f"Ollama retornou erro {response.status_code}. "
                         f"Verifique se o Ollama está rodando."
            })

        # Extrai o texto gerado pela IA do campo "response" do JSON do Ollama
        raw = response.json().get("response", "").strip()

        # --- Extrai o JSON da resposta da IA ---
        # O modelo pode incluir texto antes/depois do JSON ou
        # envolvê-lo em ```json ... ```. O regex extrai apenas
        # o objeto JSON independente do que vier ao redor.
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            raw = json_match.group(0)

        # Converte a string JSON em dicionário Python e retorna ao front-end
        result = json.loads(raw)
        return jsonify(result)

    except requests.exceptions.ConnectionError:
        # O Ollama não está rodando ou não está acessível na porta 11434
        return jsonify({
            "error": "Ollama não está rodando. "
                     "Abra um terminal e execute: ollama serve"
        })

    except json.JSONDecodeError:
        # A IA retornou um texto que não é um JSON válido
        # (pode acontecer com prompts muito longos ou modelo sobrecarregado)
        return jsonify({
            "error": "Não foi possível processar a análise. Tente novamente."
        })

    except Exception as e:
        # Captura qualquer outro erro não previsto e retorna a mensagem
        return jsonify({"error": f"Erro inesperado: {str(e)}"})


# =============================================================
# PONTO DE ENTRADA — Inicia o servidor Flask
# =============================================================
if __name__ == '__main__':
    # Exibe informações de inicialização no terminal
    print("=" * 55)
    print("  StockMind — Análise de Ações com IA")
    print("  Powered by Ollama — 100% Local & Gratuito")
    print("=" * 55)
    print("  Acesse: http://localhost:5000")
    print("  Pressione Ctrl+C para encerrar")
    print("=" * 55)

    # Inicia o servidor Flask
    # debug=False  → modo produção (sem recarregamento automático)
    # host='0.0.0.0'→ aceita conexões de qualquer IP da rede local
    # port=5000    → porta padrão do Flask
    app.run(debug=False, host='0.0.0.0', port=5000)
