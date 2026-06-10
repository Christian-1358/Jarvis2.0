# Jarvis MiniMax

Assistente de automação de PC controlado por IA da MiniMax.

## Como funciona

```
Você: "jarvis pesquise sobre Python"
       ↓
┌─────────────────────────────────────┐
│  Jarvis MiniMax                      │
│  (envia comando para API MiniMax)    │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│  MiniMax API                         │
│  (analisa e decide a ação)           │
│  → {"action": "search_web",         │
│     "target": "Python"}              │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│  Jarvis MiniMax                      │
│  (executa ação localmente)           │
│  → Abre Google pesquisando Python    │
└─────────────────────────────────────┘
```

## Instalação

```bash
# Clonar ou copiar para Documents
cd ~/Documents/JarvisMiniMax

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Configuração

### 1. Configure sua API Key da MiniMax

Edite o arquivo `config/settings.py`:

```python
MINIMAX_API_KEY = "sua_api_key_aqui"
MINIMAX_API_ID = "seu_group_id_aqui"  # opcional
```

Ou exporte como variável de ambiente:

```bash
export MINIMAX_API_KEY='sua_key_aqui'
export MINIMAX_API_ID='seu_id_aqui'
```

### 2. (Opcional) Configure sua chave no arquivo `.env`

Crie um arquivo `.env` na raiz do projeto:

```
MINIMAX_API_KEY=sua_api_key_aqui
MINIMAX_API_ID=sua_api_id_aqui
```

## Uso

### Modo Terminal (padrão)

```bash
python main.py
```

Digite seus comandos diretamente. Exemplo:
```
Você: jarvis abra o chrome
Você: pesquise receitas de bolo
Você: tire um screenshot
```

### Modo Voz

```bash
python main.py --voice
```

Diga "jarvis" seguido do comando. Exemplo:
```
"jarvis abra o chrome"
"jarvis pesquise sobre inteligência artificial"
"jarvis tire um print"
```

### Modo API (para integrações)

```bash
python main.py --api 8765
```

Envia comandos via HTTP:
```bash
curl -X POST http://localhost:8765/command \
  -H "Content-Type: application/json" \
  -d '{"command": "abra o chrome"}'
```

## Ações Disponíveis

| Ação | Descrição | Exemplo |
|------|-----------|---------|
| `search_web` | Pesquisar no Google | "pesquise Python" |
| `open_app` | Abrir aplicativo | "abra o chrome" |
| `open_site` | Abrir site | "abra youtube.com" |
| `close_app` | Fechar aplicativo | "feche o chrome" |
| `type_text` | Digitar texto | "digite olá mundo" |
| `press_key` | Pressionar tecla | "pressione enter" |
| `screenshot` | Tirar screenshot | "tire um print" |
| `volume_up` | Aumentar volume | "aumente o volume" |
| `volume_down` | Baixar volume | "diminua o volume" |
| `mute` | Mutar som | "muta o som" |
| `shutdown_pc` | Desligar PC | "desliga o pc" |
| `restart_pc` | Reiniciar PC | "reinicia o pc" |
| `open_folder` | Abrir pasta | "abra a pasta documentos" |
| `create_file` | Criar arquivo | "crie arquivo teste.txt" |
| `read_file` | Ler arquivo | "leia o arquivo teste.txt" |
| `delete_file` | Deletar arquivo | "delete teste.txt" |
| `rename_file` | Renomear arquivo | "renomeia teste.txt para novo.txt" |
| `move_file` | Mover arquivo | "move teste.txt para documentos" |
| `copy_file` | Copiar arquivo | "copia teste.txt para backup" |
| `run_command` | Executar comando | "execute ls -la" |
| `chat` | Conversa livre | "olá tudo bem?" |

## Adicionando novas ações

1. **Crie a função** em `functions/__init__.py`:

```python
def minha_nova_acao(param: str) -> str:
    # Sua lógica aqui
    return "Resultado"
```

2. **Adicione ao dicionário FUNCTIONS**:

```python
FUNCTIONS = {
    # ... outras ações ...
    "minha_nova_acao": minha_nova_acao,
}
```

3. **Atualize o prompt do sistema** em `core/minimax_client.py` na função `_build_system_prompt()` para incluir a nova ação.

## Estrutura do projeto

```
JarvisMiniMax/
├── main.py                 # Ponto de entrada
├── requirements.txt        # Dependências
├── config/
│   └── settings.py        # Configurações
├── core/
│   └── minimax_client.py  # Cliente API MiniMax
├── functions/
│   └── __init__.py        # Funções de automação
└── dados/                  # Dados gerados (screenshots, etc)
```

## Requisitos

- Python 3.8+
- API Key da MiniMax (obtenha em minimax.io)
- Para modo voz: microfone + PyAudio

## Resolução de problemas

### "MINIMAX_API_KEY não configurada"
```bash
export MINIMAX_API_KEY='sua_key_aqui'
```

### Erro de microfone no modo voz
```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev
pip install pyaudio

# macOS
brew install portaudio
pip install pyaudio
```

### pyautogui não funciona
```bash
pip install pyautogui
```

## Licença

MIT License - Use livremente.# Jarvis2.0
