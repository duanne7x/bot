"""
Configurações e mensagens do bot
"""

# Configurações da API
API_BASE_URL = "https://7xhublikes.space"
API_ENDPOINT = "/api/sendlikes"
MIN_LIKES_REQUIRED = 100

# Arquivos e diretórios
DATA_DIR = "data"
API_KEY_FILE = f"{DATA_DIR}/api_key.txt"
DATABASE_FILE = f"{DATA_DIR}/bot_database.db"

# Mensagens do bot
MESSAGES = {
    "start": """
🎮 *BEM-VINDO AO BOT DE LIKES AUTOMÁTICOS!*

Este bot envia likes automaticamente à meia-noite (00:00) todos os dias para seus IDs cadastrados!

📋 *COMANDOS DISPONÍVEIS:*

/addid \[ID\] - Adicionar um ID do jogo
/myids - Ver seus IDs cadastrados
/removeids - Remover IDs
/like \[ID\] - Enviar likes AGORA
/status - Status do sistema
/help - Ajuda completa

💡 *Use o menu abaixo para navegar facilmente!*
""",

    "help": """
📖 *GUIA COMPLETO DO BOT*

*COMANDOS PRINCIPAIS:*

/addid \[ID\] - Adicionar ID do jogo à sua lista
Exemplo: `/addid 1033857091`

/myids - Ver todos os seus IDs cadastrados

/removeids - Remover IDs indesejados

/like \[ID\] - Enviar likes imediatamente
Exemplo: `/like 1033857091`

/status - Ver status do sistema

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*COMO FUNCIONA:*

1️⃣ Cadastre seus IDs usando /addid
2️⃣ Todo dia à meia-noite o bot envia likes automaticamente
3️⃣ Você pode enviar likes manualmente com /like quando quiser
4️⃣ Receba notificações de todos os envios

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*IMPORTANTE:*

• Cada envio deve ter no mínimo 100 likes para ser válido
• Você pode cadastrar múltiplos IDs
• Envios automáticos acontecem às 00:00 (horário Brasil)

❓ Dúvidas? Entre em contato com o administrador!
""",

    "admin_help": """
👑 *COMANDOS DE ADMINISTRADOR*

/setkey \[KEY\] - Configurar key da API
/checkkey - Ver status da key
/listusers - Listar todos os usuários
/stats - Estatísticas gerais
/broadcast \[msg\] - Enviar mensagem para todos
/forcesend - Forçar envio de teste manual

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*ATENÇÃO:*
A key da API tem limite de 200 requisições por dia.
Apenas envios com 100+ likes são contabilizados.
""",
}

# Botões do menu
MENU_BUTTONS = [
    [
        {"text": "➕ Adicionar ID", "callback_data": "menu_addid"},
        {"text": "📋 Meus IDs", "callback_data": "menu_myids"}
    ],
    [
        {"text": "💖 Enviar Likes", "callback_data": "menu_like"},
        {"text": "🗑️ Remover ID", "callback_data": "menu_remove"}
    ],
    [
        {"text": "📊 Status", "callback_data": "menu_status"},
        {"text": "❓ Ajuda", "callback_data": "menu_help"}
    ]
]