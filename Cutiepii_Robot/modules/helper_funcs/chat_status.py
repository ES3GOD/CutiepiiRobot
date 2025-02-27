"""
BSD 2-Clause License

Copyright (C) 2017-2019, Paul Larsen
Copyright (C) 2021-2022, Awesome-RJ, <https://github.com/Awesome-RJ>
Copyright (c) 2021-2022, Yūki • Black Knights Union, <https://github.com/Awesome-RJ/CutiepiiRobot>

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import contextlib
import requests

from time import perf_counter
from functools import wraps
from cachetools import TTLCache
from threading import RLock
from Cutiepii_Robot.modules.sql.moderators_sql import is_modd
from Cutiepii_Robot import (
    DEL_CMDS,
    DEV_USERS,
    SUDO_USERS,
    SUPPORT_CHAT,
    SUPPORT_USERS,
    TIGER_USERS,
    WHITELIST_USERS,
    CUTIEPII_PTB,
    TOKEN,
    OWNER_ID,

)

from Cutiepii_Robot.modules.helper_funcs.admin_status import bot_is_admin

from telegram import Chat, ChatMember, Update, User
from telegram.constants import ParseMode, ChatType
from telegram.ext import CallbackContext

# stores admemes in memory for 10 min.
ADMIN_CACHE = TTLCache(maxsize=512, ttl=60 * 10, timer=perf_counter)
THREAD_LOCK = RLock()
anonymous_data = {}

def can_manage_video_chats(chat_id, user_id):
	result = requests.post(f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={chat_id}&user_id={user_id}")
	status = result.json()["ok"]

	if status is True:
		data = result.json()["result"]["can_manage_video_chats"]
		return data
	return False

def is_anon(user: User, chat: Chat):
    return chat.get_member(user.id).is_anonymous

def is_whitelist_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return any(user_id in user for user in [WHITELIST_USERS, TIGER_USERS, SUPPORT_USERS, SUDO_USERS, DEV_USERS])


def is_support_plus(_: Chat, user_id: int) -> bool:
    return user_id in SUPPORT_USERS or user_id in SUDO_USERS or user_id in DEV_USERS


def is_sudo_plus(_: Chat, user_id: int) -> bool:
    return user_id in SUDO_USERS or user_id in DEV_USERS

def is_stats_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return user_id in DEV_USERS

def user_can_changeinfo(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_change_info

def owner_plus(func):
    @wraps(func)
    async def is_owner_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user

        if user.id == OWNER_ID:
            return func(update, context, *args, **kwargs)
        if not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except:
                pass
        else:
            await update.effective_message.reply_text(
                "This is a restricted command."
                " You do not have permissions to run this."
            )

    return is_owner_plus_func

def user_can_ban(func):

    @wraps(func)
    async def user_banner(update, context, *args, **kwargs):


        user = update.effective_user.id
        member = await update.effective_chat.get_member(user)

        if not (member.can_restrict_members or
                member.status == "creator") and not user in SUDO_USERS:
            await update.effective_message.reply_text(
                "You are missing the following rights to use this command: \nCanRestrictUsers.")
            return ""

        return func(update, context, *args, **kwargs)

    return user_banner


def user_can_change(func):	

    @wraps(func)	
    async def info_changer(update, context, *args, **kwargs):	
        user = update.effective_user.id	
        member = await update.effective_chat.get_member(user)	


        if not (member.can_change_info or member.status == "creator") and not user in SUDO_USERS:
            await update.effective_message.reply_text("You are missing the following rights to use this command: \nCanChangeInfo")

            return ""	

        return func(update, context, *args, **kwargs)	

    return info_changer

def user_can_promote(func):
    @wraps(func)
    async def user_is_promoter(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        if not user:
            return
        user = user.id
        member = await update.effective_chat.get_member(user)
        no_rights = "You do not have 'add admin' rights."
        if (
            not (member.can_promote_members or member.status == "creator")
            and user not in SUDO_USERS
            and user not in [777000, 1087968824]
        ):
            if not update.callback_query:
                await update.effective_message.reply_text(no_rights)
            else:
                update.callback_query.answer(no_rights, show_alert=True)
            return ""
        return func(update, context, *args, **kwargs)

    return user_is_promoter

def user_can_pin(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_pin_messages
"""
def is_user_admin(update: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in DEV_USERS
        or user_id in {777000, 1087968824}
        or chat.all_members_are_administrators
    ):
        return True

    if not member:
        with THREAD_LOCK:
            # try to fetch from cache first.
            try:
                return user_id in ADMIN_CACHE[chat.id]
            except KeyError:
                # keyerror happend means cache is deleted,
                # so query bot api again and return user status
                # while saving it in cache for future useage...
                try:
                    chat_admins = CUTIEPII_PTB.await bot.getChatAdministrators(chat.id)
                    admin_list = [x.user.id for x in chat_admins]
                    ADMIN_CACHE[chat.id] = admin_list

                    if user_id in admin_list:
                        return True
                except Forbidden:
                    return False
"""
async def is_user_admin(update: Update, user_id: int, member: ChatMember = None) -> bool:
    chat = update.effective_chat
    msg = update.effective_message
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or chat.all_members_are_administrators
        or (
            msg.reply_to_message
            and msg.reply_to_message.sender_chat is not None
            and msg.reply_to_message.sender_chat.type != "channel"
        )
    ):
        return True

    if not member:
        # try to fetch from cache first.
        try:
            return user_id in ADMIN_CACHE[chat.id]
        except KeyError:
            # KeyError happened means cache is deleted,
            # so query bot api again and return user status
            # while saving it in cache for future usage...
            chat_admins = await CUTIEPII_PTB.bot.getChatAdministrators(chat.id)
            admin_list = [x.user.id for x in chat_admins]
            ADMIN_CACHE[chat.id] = admin_list

            if user_id in admin_list:
                return True
            return False



def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages

"""
def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or user_id in WHITELIST_USERS
	or is_modd(chat.id, user_id)
    ):
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ("administrator", "creator")
"""

def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ("left", "kicked")

def is_user_ban_protected(update: Update, user_id: int, member: ChatMember = None) -> bool:
    chat = update.effective_chat
    msg = update.effective_message
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in DEV_USERS
        or user_id in WHITELIST_USERS
        or user_id in TIGER_USERS
        or is_modd(chat.id, user_id)
        or chat.all_members_are_administrators
        or (msg.reply_to_message and msg.reply_to_message.sender_chat is not None and 
	    msg.reply_to_message.sender_chat.type != "channel")
    ):
        return True

    if not member:
        member = chat.get_member(user_id)

    return member.status in ("administrator", "creator")

def dev_plus(func):
    @wraps(func)
    async def is_dev_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user

        if user.id in DEV_USERS:
            return func(update, context, *args, **kwargs)
        if not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except:
                pass
        else:
            await update.effective_message.reply_text(
                "This is a developer restricted command."
                "You do not have permissions to run this.",
            )

    return is_dev_plus_func


def sudo_plus(func):
    @wraps(func)
    async def is_sudo_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_sudo_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        if not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except:
                pass
        else:
            await update.effective_message.reply_text(
                "At Least be an Admin to use these all Commands",
            )

    return is_sudo_plus_func

def stats_plus(func):
    @wraps(func)
    async def is_stats_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_stats_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        if not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except:
                pass
        else:
            await update.effective_message.reply_text(
                "Yuzuki stats is just for Dev User",
            )

    return is_sudo_plus_func


def support_plus(func):
    @wraps(func)
    async def is_support_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_support_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        if DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except:
                pass

    return is_support_plus_func


def whitelist_plus(func):
    @wraps(func)
    async def is_whitelist_plus_func(
        update: Update, context: CallbackContext, *args, **kwargs,
    ):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_whitelist_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(
            f"You don't have access to use this.\nVisit @{SUPPORT_CHAT}",
        )

    return is_whitelist_plus_func


def user_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user
        # chat = update.effective_chat

        if user and (await is_user_admin(update, user.id)):
            return func(update, context, *args, **kwargs)
        if not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            with contextlib.suppress(TelegramError):
                await update.effective_message.delete()
        else:
            await update.effective_message.reply_text(
                "Who dis non-admin telling me what to do?"
            )

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    async def is_not_admin_no_reply(
        update: Update, context: CallbackContext, *args, **kwargs
    ):
        # bot = context.bot
        user = update.effective_user
        # chat = update.effective_chat

        if user and (await is_user_admin(update, user.id)):
            return func(update, context, *args, **kwargs)
        if not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            with contextlib.suppress(TelegramError):
                await update.effective_message.delete()

    return is_not_admin_no_reply


def user_not_admin(func):
    @wraps(func)
    async def is_not_admin(update: Update, context: CallbackContext, *args, **kwargs):
        message = update.effective_message
        user = update.effective_user
        # chat = update.effective_chat

        if message.is_automatic_forward:
            return
        if message.sender_chat and message.sender_chat.type != "channel":
            return
        if user and not (await is_user_admin(update, user.id)):
            return func(update, context, *args, **kwargs)

        if not user:
            pass

    return is_not_admin


def bot_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            not_admin = "I'm not an admin in this chat, how about you promote me first?"
        else:
            not_admin = f"I'm not admin in <b>{update_chat_title}</b>, how about you promote me first?"

        if bot_is_admin(update.effective_chat, context.bot.id):
            return func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(not_admin, parse_mode=ParseMode.HTML)

    return is_admin


def bot_can_delete(func):
    @wraps(func)
    async def delete_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_delete = "I can't delete messages here!\nMake sure I'm admin and can delete other user's messages."
        else:
            cant_delete = f"I can't delete messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and can delete other user's messages there."

        if can_delete(chat, bot.id):
            return func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(cant_delete, parse_mode=ParseMode.HTML)

    return delete_rights


def can_pin(func):
    @wraps(func)
    async def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_pin = (
                "I can't pin messages here!\nMake sure I'm admin and can pin messages."
            )
        else:
            cant_pin = f"I can't pin messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and can pin messages there."

        if chat.get_member(CUTIEPII_PTB.bot.id).can_pin_messages:
            return func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(cant_pin, parse_mode=ParseMode.HTML)

    return pin_rights


def can_promote(func):
    @wraps(func)
    async def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_promote = "I can't promote/demote people here!\nMake sure I'm admin and can appoint new admins."
        else:
            cant_promote = (
                f"I can't promote/demote people in <b>{update_chat_title}</b>!\n"
                f"Make sure I'm admin there and have the permission to appoint new admins."
            )

        if chat.get_member(CUTIEPII_PTB.bot.id).can_promote_members:
            return func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(cant_promote, parse_mode=ParseMode.HTML)

    return promote_rights


def can_restrict(func):
    @wraps(func)
    async def restrict_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_restrict = "I can't restrict people here!\nMake sure I'm admin and can restrict users."
        else:
            cant_restrict = (
                f"I can't restrict people in <b>{update_chat_title}</b>!\nMake sure I'm admin there and "
                f"can restrict users. "
            )

        if (await chat.get_member(CUTIEPII_PTB.bot.id)).can_restrict_members:
            return func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(
            cant_restrict, parse_mode=ParseMode.HTML
        )

    return restrict_rights


def user_can_ban(func):
    @wraps(func)
    async def user_is_banhammer(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user.id
        member = await update.effective_chat.get_member(user)

        if not member.can_restrict_members and member.status != "creator" and user not in SUDO_USERS:
            await update.effective_message.reply_text(
                "Sorry son, but you're not worthy to wield the banhammer."
            )
            return ""

        return func(update, context, *args, **kwargs)

    return user_is_banhammer


def connection_status(func):
    @wraps(func)
    async def connected_status(update: Update, context: CallbackContext, *args, **kwargs):
        if not (update.effective_chat or update.effective_user):
            return
        if conn := await connected(context.bot, update, update.effective_chat, update.effective_user.id, need_admin=False):
            chat = CUTIEPII_PTB.bot.getChat(conn)
            await update.__setattr__("_effective_chat", chat)
        elif update.effective_message.chat.type == ChatType.PRIVATE:
            await update.effective_message.reply_text(
                "Send /connect in a group that you and I have in common first."
            )
            return connected_status

        return func(update, context, *args, **kwargs)

    return connected_status

# Workaround for circular import with connection.py
from Cutiepii_Robot.modules import connection

connected = connection.connected
