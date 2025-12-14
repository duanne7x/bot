"""
Bot de Telegram para envio automático de likes
"""
import os
import re
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)

import database as db
import api_client as api
from scheduler import LikesScheduler
from config import MESSAGES, MENU_BUTTONS, MIN_LIKES_REQUIRED

# Carregar variáveis de ambiente
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Variável global para o scheduler
scheduler = None


def is_admin(user_id: int) -> bool:
    """Verifica se o usuário é admin"""
    return user_id == ADMIN_ID


def escape_markdown(text: str) -> str:
    """
    Escapa caracteres especiais do Markdown
    
    Args:
        text: Texto a ser escapado
        
    Returns:
        str: Texto escapado
    """
    if not text:
        return "N/A"
    
    # Caracteres que precisam ser escapados no Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def create_menu_keyboard():
    """Cria o teclado do menu principal"""
    keyboard = []
    for row in MENU_BUTTONS:
        keyboard.append([
            InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])
            for btn in row
        ])
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    
    # Adicionar usuário ao banco
    await db.add_user(user.id, user.username)
    
    # Enviar mensagem de boas-vindas
    await update.message.reply_text(
        MESSAGES["start"],
        parse_mode='Markdown',
        reply_markup=create_menu_keyboard()
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /menu"""
    await update.message.reply_text(
        "📋 *MENU PRINCIPAL*\n\nEscolha uma opção:",
        parse_mode='Markdown',
        reply_markup=create_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    user_id = update.effective_user.id
    
    # Mensagem de ajuda normal
    help_text = MESSAGES["help"]
    
    # Adicionar comandos admin se for admin
    if is_admin(user_id):
        help_text += "\n\n" + MESSAGES["admin_help"]
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def addid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /addid [ID]"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Verificar se o ID foi fornecido
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso incorreto!*\n\n"
            "Use: `/addid [ID]`\n"
            "Exemplo: `/addid 1033857091`",
            parse_mode='Markdown'
        )
        return
    
    game_id = context.args[0]
    
    # Validar se é apenas números
    if not game_id.isdigit():
        await update.message.reply_text(
            "❌ *ID inválido!*\n\n"
            "O ID deve conter apenas números.\n"
            "Exemplo: `1033857091`",
            parse_mode='Markdown'
        )
        return
    
    # Adicionar ao banco
    is_new_user = await db.add_user(user_id, username)
    success, message = await db.add_game_id(user_id, game_id)
    
    await update.message.reply_text(message, parse_mode='Markdown')
    
    # Notificar admin se for novo usuário
    if is_new_user and success:
        try:
            safe_username = escape_markdown(username) if username else 'N/A'
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🆕 *NOVO USUÁRIO CADASTRADO!*\n\n"
                     f"👤 Username: @{safe_username}\n"
                     f"🆔 Telegram ID: `{user_id}`\n"
                     f"🎮 Game ID: `{game_id}`\n"
                     f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ Erro ao notificar admin: {e}")


async def myids_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /myids"""
    user_id = update.effective_user.id
    
    # Buscar IDs do usuário
    game_ids = await db.get_user_game_ids(user_id)
    
    if not game_ids:
        await update.message.reply_text(
            "📋 *SEUS IDs*\n\n"
            "Você ainda não tem nenhum ID cadastrado.\n\n"
            "Use `/addid [ID]` para adicionar.",
            parse_mode='Markdown'
        )
        return
    
    # Montar mensagem
    message = "📋 *SEUS IDs CADASTRADOS*\n\n"
    
    for idx, game_id_info in enumerate(game_ids, 1):
        message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"*#{idx}* - `{game_id_info['game_id']}`\n"
        
        if game_id_info['player_name']:
            safe_player = escape_markdown(game_id_info['player_name'])
            message += f"👤 Player: {safe_player}\n"
        
        if game_id_info['total_likes_received'] > 0:
            total = api.format_number(game_id_info['total_likes_received'])
            message += f"💖 Total de likes recebidos: {total}\n"
        
        if game_id_info['last_likes_sent']:
            safe_date = escape_markdown(game_id_info['last_likes_sent'])
            message += f"📅 Último envio: {safe_date}\n"
        else:
            message += f"📅 Ainda não recebeu likes\n"
        
        message += f"🕐 Próximo envio: Hoje às 00:00\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"📊 *Total:* {len(game_ids)} ID(s) cadastrado(s)"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def removeids_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /removeids"""
    user_id = update.effective_user.id
    
    # Buscar IDs do usuário
    game_ids = await db.get_user_game_ids(user_id)
    
    if not game_ids:
        await update.message.reply_text(
            "📋 *REMOVER IDs*\n\n"
            "Você não tem nenhum ID cadastrado.",
            parse_mode='Markdown'
        )
        return
    
    # Criar botões
    keyboard = []
    for game_id_info in game_ids:
        gid = game_id_info['game_id']
        player = game_id_info['player_name'] or gid
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {player[:30]}",
                callback_data=f"remove_{gid}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("❌ Cancelar", callback_data="remove_cancel")
    ])
    
    await update.message.reply_text(
        "🗑️ *REMOVER IDs*\n\n"
        "Selecione o ID que deseja remover:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /like [ID] - Envia likes imediatamente"""
    user_id = update.effective_user.id
    
    # Verificar se o ID foi fornecido
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso incorreto!*\n\n"
            "Use: `/like [ID]`\n"
            "Exemplo: `/like 1033857091`",
            parse_mode='Markdown'
        )
        return
    
    game_id = context.args[0]
    
    # Validar se é apenas números
    if not game_id.isdigit():
        await update.message.reply_text(
            "❌ *ID inválido!*\n\n"
            "O ID deve conter apenas números.",
            parse_mode='Markdown'
        )
        return
    
    # Mensagem de aguardo
    waiting_msg = await update.message.reply_text(
        "⏳ *ENVIANDO LIKES...*\n\n"
        f"🆔 ID: `{game_id}`\n\n"
        "Por favor, aguarde...",
        parse_mode='Markdown'
    )
    
    # Carregar key da API
    api_key = await api.load_key()
    if not api_key:
        await waiting_msg.edit_text(
            "❌ *ERRO DE CONFIGURAÇÃO*\n\n"
            "A API não está configurada.\n"
            "Contate o administrador.",
            parse_mode='Markdown'
        )
        return
    
    # Enviar likes
    response = api.send_likes(game_id, api_key)
    
    # Processar resposta
    if response.get("success") and response.get("likesAdded", 0) >= MIN_LIKES_REQUIRED:
        # Sucesso
        likes_added = response.get("likesAdded", 0)
        player_name = response.get("player", "N/A")
        
        # Atualizar banco
        await db.update_game_id_info(user_id, game_id, player_name, likes_added)
        await db.log_send(user_id, game_id, likes_added, True, None, player_name, False)
        
        # Mensagem de sucesso
        message = api.format_success_message(response)
        
    elif not response.get("success") and response.get("error") == "INSUFFICIENT_LIKES":
        # Envio parcial
        likes_added = response.get("likesAdded", 0)
        player_name = response.get("player", "N/A")
        
        await db.log_send(user_id, game_id, likes_added, False, "Menos de 100 likes", player_name, False)
        
        message = api.format_partial_message(response)
        
    else:
        # Erro
        error_msg = response.get("message", "Erro desconhecido")
        await db.log_send(user_id, game_id, 0, False, error_msg, None, False)
        
        message = api.format_error_message(response, game_id)
    
    await waiting_msg.edit_text(message, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    user_id = update.effective_user.id
    
    # Buscar IDs do usuário
    game_ids = await db.get_user_game_ids(user_id)
    
    message = f"""📊 *STATUS DO SISTEMA*

👤 Seu Telegram ID: `{user_id}`
🆔 IDs cadastrados: {len(game_ids)}
⏰ Próximo envio automático: Hoje às 00:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Sistema operacional
🔄 Envios automáticos ativos
💖 Bot funcionando normalmente

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


# ============ COMANDOS ADMIN ============

async def setkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /setkey [KEY] - Admin apenas"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Comando disponível apenas para administradores.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso incorreto!*\n\n"
            "Use: `/setkey [KEY]`",
            parse_mode='Markdown'
        )
        return
    
    api_key = context.args[0]
    
    # Salvar key
    success = await api.save_key(api_key)
    
    if success:
        # Deletar mensagem com a key por segurança
        try:
            await update.message.delete()
        except:
            pass
        
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ *KEY CONFIGURADA COM SUCESSO!*\n\n"
                 "A key foi salva e o bot está pronto para usar.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ *ERRO AO SALVAR KEY*\n\n"
            "Não foi possível salvar a key.",
            parse_mode='Markdown'
        )


async def checkkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /checkkey - Admin apenas"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Comando disponível apenas para administradores.")
        return
    
    # Carregar key
    api_key = await api.load_key()
    
    if not api_key:
        await update.message.reply_text(
            "❌ *KEY NÃO CONFIGURADA*\n\n"
            "Use `/setkey [KEY]` para configurar.",
            parse_mode='Markdown'
        )
        return
    
    # Mostrar parcialmente (primeiros 8 e últimos 8 caracteres)
    masked_key = f"{api_key[:8]}...{api_key[-8:]}"
    
    message = f"""🔑 *STATUS DA KEY*

📋 Key: `{masked_key}`
✅ Status: Configurada
📅 Configurada em: Sistema operacional

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️ A key completa não é exibida por segurança.

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /listusers - Admin apenas"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Comando disponível apenas para administradores.")
        return
    
    # Buscar usuários
    users = await db.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "📋 *LISTA DE USUÁRIOS*\n\n"
            "Nenhum usuário cadastrado.",
            parse_mode='Markdown'
        )
        return
    
    message = f"👥 *LISTA DE USUÁRIOS*\n\n"
    message += f"Total: {len(users)} usuário(s)\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, user in enumerate(users, 1):
        username = escape_markdown(user['username']) if user['username'] else 'N/A'
        message += f"*#{idx}*\n"
        message += f"👤 Username: @{username}\n"
        message += f"🆔 ID: `{user['telegram_id']}`\n"
        message += f"📅 Registro: {escape_markdown(user['registered_at'])}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats - Admin apenas"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Comando disponível apenas para administradores.")
        return
    
    # Buscar estatísticas
    stats = await db.get_stats()
    
    message = f"""📊 *ESTATÍSTICAS GERAIS*

👥 Total de usuários: {stats.get('total_users', 0)}
🆔 Total de IDs cadastrados: {stats.get('total_ids', 0)}
💖 Total de likes enviados: {api.format_number(stats.get('total_likes', 0))}

📅 Envios nas últimas 24h: {stats.get('last_24h', 0)}
✅ Taxa de sucesso: {stats.get('success_rate', 0):.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /broadcast [mensagem] - Admin apenas"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Comando disponível apenas para administradores.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso incorreto!*\n\n"
            "Use: `/broadcast [mensagem]`\n"
            "Exemplo: `/broadcast Olá a todos!`",
            parse_mode='Markdown'
        )
        return
    
    # Montar mensagem
    broadcast_message = " ".join(context.args)
    
    # Buscar todos os usuários
    users = await db.get_all_users()
    
    success_count = 0
    failure_count = 0
    
    # Enviar para cada usuário
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=f"📢 *MENSAGEM DO ADMINISTRADOR*\n\n{broadcast_message}",
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Erro ao enviar para {user['telegram_id']}: {e}")
            failure_count += 1
    
    # Relatório
    await update.message.reply_text(
        f"📊 *RELATÓRIO DE BROADCAST*\n\n"
        f"✅ Enviadas: {success_count}\n"
        f"❌ Falharam: {failure_count}\n"
        f"📊 Total: {len(users)}",
        parse_mode='Markdown'
    )


async def forcesend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /forcesend - Admin apenas - Força envio manual"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Comando disponível apenas para administradores.")
        return
    
    await update.message.reply_text(
        "🔧 *FORÇANDO ENVIO MANUAL*\n\n"
        "Processando todos os IDs cadastrados...",
        parse_mode='Markdown'
    )
    
    # Forçar envio
    await scheduler.force_send()
    
    await update.message.reply_text(
        "✅ *ENVIO MANUAL CONCLUÍDO*\n\n"
        "Verifique as notificações enviadas aos usuários.",
        parse_mode='Markdown'
    )


# ============ HANDLERS DE CALLBACKS ============

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para callbacks dos botões do menu"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = query.from_user.id
    
    if callback_data == "menu_addid":
        await query.message.reply_text(
            "➕ *ADICIONAR ID*\n\n"
            "Use o comando:\n"
            "`/addid [ID]`\n\n"
            "Exemplo:\n"
            "`/addid 1033857091`",
            parse_mode='Markdown'
        )
    
    elif callback_data == "menu_myids":
        # Buscar IDs do usuário
        game_ids = await db.get_user_game_ids(user_id)
        
        if not game_ids:
            await query.message.reply_text(
                "📋 *SEUS IDs*\n\n"
                "Você ainda não tem nenhum ID cadastrado.\n\n"
                "Use `/addid [ID]` para adicionar.",
                parse_mode='Markdown'
            )
            return
        
        # Montar mensagem
        message = "📋 *SEUS IDs CADASTRADOS*\n\n"
        
        for idx, game_id_info in enumerate(game_ids, 1):
            message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"*#{idx}* - `{game_id_info['game_id']}`\n"
            
            if game_id_info['player_name']:
                safe_player = escape_markdown(game_id_info['player_name'])
                message += f"👤 Player: {safe_player}\n"
            
            if game_id_info['total_likes_received'] > 0:
                total = api.format_number(game_id_info['total_likes_received'])
                message += f"💖 Total de likes recebidos: {total}\n"
            
            if game_id_info['last_likes_sent']:
                safe_date = escape_markdown(game_id_info['last_likes_sent'])
                message += f"📅 Último envio: {safe_date}\n"
            else:
                message += f"📅 Ainda não recebeu likes\n"
            
            message += f"🕐 Próximo envio: Hoje às 00:00\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"📊 *Total:* {len(game_ids)} ID(s) cadastrado(s)"
        
        await query.message.reply_text(message, parse_mode='Markdown')
    
    elif callback_data == "menu_like":
        await query.message.reply_text(
            "💖 *ENVIAR LIKES*\n\n"
            "Use o comando:\n"
            "`/like [ID]`\n\n"
            "Exemplo:\n"
            "`/like 1033857091`",
            parse_mode='Markdown'
        )
    
    elif callback_data == "menu_remove":
        # Buscar IDs do usuário
        game_ids = await db.get_user_game_ids(user_id)
        
        if not game_ids:
            await query.message.reply_text(
                "📋 *REMOVER IDs*\n\n"
                "Você não tem nenhum ID cadastrado.",
                parse_mode='Markdown'
            )
            return
        
        # Criar botões
        keyboard = []
        for game_id_info in game_ids:
            gid = game_id_info['game_id']
            player = game_id_info['player_name'] or gid
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {player[:30]}",
                    callback_data=f"remove_{gid}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Cancelar", callback_data="remove_cancel")
        ])
        
        await query.message.reply_text(
            "🗑️ *REMOVER IDs*\n\n"
            "Selecione o ID que deseja remover:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif callback_data == "menu_status":
        # Buscar IDs do usuário
        game_ids = await db.get_user_game_ids(user_id)
        
        message = f"""📊 *STATUS DO SISTEMA*

👤 Seu Telegram ID: `{user_id}`
🆔 IDs cadastrados: {len(game_ids)}
⏰ Próximo envio automático: Hoje às 00:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Sistema operacional
🔄 Envios automáticos ativos
💖 Bot funcionando normalmente

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
        
        await query.message.reply_text(message, parse_mode='Markdown')
    
    elif callback_data == "menu_help":
        # Mensagem de ajuda normal
        help_text = MESSAGES["help"]
        
        # Adicionar comandos admin se for admin
        if is_admin(user_id):
            help_text += "\n\n" + MESSAGES["admin_help"]
        
        await query.message.reply_text(help_text, parse_mode='Markdown')


async def remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para callbacks de remoção de IDs"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = query.from_user.id
    
    if callback_data == "remove_cancel":
        await query.message.edit_text(
            "❌ *Cancelado*\n\nNenhum ID foi removido.",
            parse_mode='Markdown'
        )
        return
    
    # Extrair game_id do callback
    if callback_data.startswith("remove_"):
        game_id = callback_data.replace("remove_", "")
        
        # Remover do banco
        success = await db.remove_game_id(user_id, game_id)
        
        if success:
            await query.message.edit_text(
                f"✅ *ID REMOVIDO*\n\n"
                f"🆔 ID `{game_id}` foi removido da sua lista.\n\n"
                f"Este ID não receberá mais likes automáticos.",
                parse_mode='Markdown'
            )
        else:
            await query.message.edit_text(
                "❌ *ERRO*\n\nNão foi possível remover o ID.",
                parse_mode='Markdown'
            )


# ============ INICIALIZAÇÃO ============

async def post_init(application: Application):
    """Função executada após inicialização do bot"""
    global scheduler
    
    # Inicializar banco de dados
    await db.init_db()
    
    # Inicializar scheduler
    scheduler = LikesScheduler(application.bot, ADMIN_ID)
    await scheduler.start()
    
    print("✅ Bot inicializado com sucesso!")
    print(f"⏰ Envios automáticos agendados para 00:00 (horário Brasil)")


def main():
    """Função principal"""
    # Criar aplicação
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Adicionar handlers de comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addid", addid_command))
    app.add_handler(CommandHandler("myids", myids_command))
    app.add_handler(CommandHandler("removeids", removeids_command))
    app.add_handler(CommandHandler("like", like_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # Comandos admin
    app.add_handler(CommandHandler("setkey", setkey_command))
    app.add_handler(CommandHandler("checkkey", checkkey_command))
    app.add_handler(CommandHandler("listusers", listusers_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("forcesend", forcesend_command))
    
    # Handlers de callbacks
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(remove_callback, pattern="^remove_"))
    
    # Iniciar bot
    print("🤖 Iniciando bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()