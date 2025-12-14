#!/bin/bash

# Script de inicialização do Bot de Likes

echo "🤖 Iniciando Bot de Telegram - Envio Automático de Likes"
echo ""

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo ""
    echo "Criando arquivo .env de exemplo..."
    cat > .env << EOL
# Configurações do Bot
BOT_TOKEN=seu_token_do_botfather_aqui
ADMIN_ID=seu_telegram_id_aqui

# Exemplo:
# BOT_TOKEN=7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
# ADMIN_ID=123456789
EOL
    echo ""
    echo "❌ Por favor, edite o arquivo .env com suas informações e execute novamente."
    echo ""
    echo "   1. Obtenha o BOT_TOKEN com @BotFather no Telegram"
    echo "   2. Obtenha seu ADMIN_ID com @userinfobot no Telegram"
    echo "   3. Edite o arquivo .env"
    echo "   4. Execute: ./start.sh"
    echo ""
    exit 1
fi

# Verificar se as configurações foram preenchidas
if grep -q "seu_token_do_botfather_aqui" .env || grep -q "seu_telegram_id_aqui" .env; then
    echo "❌ Arquivo .env não configurado corretamente!"
    echo ""
    echo "   Por favor, edite o arquivo .env com:"
    echo "   1. Seu BOT_TOKEN (obtido com @BotFather)"
    echo "   2. Seu ADMIN_ID (obtido com @userinfobot)"
    echo ""
    exit 1
fi

echo "✅ Arquivo .env configurado"
echo ""

# Verificar se as dependências estão instaladas
echo "📦 Verificando dependências..."
if ! python3 -c "import telegram" &> /dev/null; then
    echo "⚠️  Dependências não encontradas. Instalando..."
    pip install -r requirements.txt
    echo ""
fi

echo "✅ Dependências verificadas"
echo ""

# Criar diretório de dados se não existir
mkdir -p data

# Iniciar o bot
echo "🚀 Iniciando bot..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 bot.py