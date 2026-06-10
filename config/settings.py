"""
Configurações do Jarvis MiniMax
Carrega variáveis do arquivo .env na raiz do projeto
"""

import os
from pathlib import Path

# Carregar variáveis do arquivo .env
from dotenv import load_dotenv

# Encontrar arquivo .env na raiz do projeto
ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # Tentar no diretório atual também
    ENV_FILE = Path.cwd() / ".env"
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

# Diretório base
BASE_DIR = Path(__file__).parent.parent

# API Keys - preencha aqui ou use variável de ambiente
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
MINIMAX_API_ID = os.getenv("MINIMAX_API_ID", "").strip()

# Endpoint da API MiniMax
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic/v1"

# Modelo a usar
MODEL_NAME = os.getenv("MODEL_NAME", "MiniMax-Text-01").strip()

# Configurações gerais
DATA_DIR = BASE_DIR / "dados"
DATA_DIR.mkdir(exist_ok=True)

# Prefixo de ativação
WAKE_WORD = "jarvis"

# Timeout para chamadas API (segundos)
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30").strip())