# 📈 StockMind — AI-Powered Stock Analysis

> Análise de ações com inteligência artificial rodando 100% localmente via Ollama + LLaMA 3.2

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)
![Ollama](https://img.shields.io/badge/Ollama-LLaMA_3.2-green)
![Status](https://img.shields.io/badge/Status-Em_desenvolvimento-yellow)

---

## 🧠 Sobre o Projeto

O **StockMind** é uma aplicação web de análise de ações impulsionada por IA, desenvolvida com Python e Flask. Ela permite que o usuário consulte informações sobre ativos financeiros e receba análises geradas por um modelo de linguagem (LLM) rodando localmente, sem depender de APIs pagas externas.

O projeto nasceu da combinação da formação em **Ciência de Dados** e **Mercado Financeiro** com a experiência prática em **Tecnologia da Informação**, com o objetivo de unir finanças e IA de forma acessível e privada.

---

## ⚙️ Stack Tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python + Flask |
| IA / LLM | Ollama (LLaMA 3.2 — local) |
| Interface | HTML + CSS (Jinja2 templates) |
| Dados | yfinance / APIs financeiras |

---

## 🚀 Funcionalidades

- 🔍 Consulta de dados de ações em tempo real
- 🤖 Análise fundamentalista gerada por IA (LLM local)
- 📊 Visualização de métricas financeiras
- 🔒 100% local — sem envio de dados para APIs externas pagas
- 🌐 Interface web simples e intuitiva

---

## 🖥️ Como Rodar Localmente

### Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.com) instalado e rodando
- Modelo LLaMA 3.2 baixado:

```bash
ollama pull llama3.2
```

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/stockmind.git
cd stockmind

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

### Executando

```bash
# Certifique-se de que o Ollama está rodando
ollama serve

# Em outro terminal, inicie a aplicação
python stock_analyst.py
```

Acesse em: `http://localhost:5000`

---

## 🔐 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (nunca suba esse arquivo para o GitHub):

```env
# Exemplo de variáveis (se aplicável)
FLASK_ENV=development
FLASK_SECRET_KEY=sua_chave_secreta_aqui
```

O arquivo `.gitignore` já está configurado para ignorar `.env`.

---

## 📁 Estrutura do Projeto

```
StockMind/
├── stock_analyst.py      # Arquivo principal da aplicação
├── requirements.txt      # Dependências Python
├── .env                  # Variáveis de ambiente (NÃO versionar)
├── .gitignore
├── templates/            # Templates HTML (Jinja2)
│   └── index.html
└── static/               # CSS, JS, imagens
```

---

## 🗺️ Roadmap

- [x] Integração com Ollama (LLaMA 3.2 local)
- [x] Interface web com Flask
- [ ] Dashboard com gráficos interativos (Plotly / Streamlit)
- [ ] Suporte a múltiplos ativos simultâneos
- [ ] Monitoramento da aplicação com Dynatrace
- [ ] Containerização com Docker

---

## 👨‍💻 Autor

**Raimundo Nonato Ferreira da Silva**  
IT Analyst | Data Science & Analytics | Python · SQL · Power BI | Finance
📍 São Paulo, SP — Brasil

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](linkedin.com/in/raimundo-nonato-ferreira-da-silva-a99453a3)

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
