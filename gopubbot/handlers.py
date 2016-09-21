import html

import simplejson as json
from tornado import gen

from .bot.update import UpdateHandler


def render_event_message(event_id, event_text, participants):
    """Render event message text."""
    text = '\U0001F37A <b>{}</b>\n<i>(id: {})</i>\n\n'.format(event_text,
                                                              event_id)
    if participants:
        users = []
        for participant in participants:
            user = json.loads(participant)
            if 'username' in user:
                name = '@' + user['username']
            else:
                name = user['first_name']
                if 'last_name' in user:
                    name += ' ' + user['last_name']
            users.append(html.escape(name))
        text += 'Идут ({}):\n{}\n'.format(len(users), ', '.join(users))
    else:
        text += 'Пока никто не идет.\n'

    return text


def get_event_keyboard(event_id, show_switch_query=False):
    """Make event message inline keyboard object."""
    inline_keyboard = []
    if show_switch_query:
        inline_keyboard.append([
            {'text': 'Позвать друзей', 'switch_inline_query': str(event_id)},
        ])

    inline_keyboard.append([
        {'text': 'Я иду!', 'callback_data': 'event_add:{}'.format(event_id)},
        {'text': 'Не пойду', 'callback_data': 'event_del:{}'.format(event_id)},
    ])
    return inline_keyboard


class EventBotCommandHandler(UpdateHandler):
    """Pub event message update handler."""

    @gen.coroutine
    def handle(self, update):
        if (update.chat['type'] != 'private' or
                update.from_user is not None and
                update.chat['id'] != update.from_user['id']):
            return

        state_key = 'user:{}:state'.format(update.from_user['id'])

        if update.bot_command == '/go':
            self.redis.set(state_key, 'go')
            text = 'Куда и во сколько?'
            yield self.api.send_message(update.chat['id'], text)


class EventMessageHandler(UpdateHandler):
    """Pub event message update handler."""

    @gen.coroutine
    def handle(self, update):
        if (update.chat['type'] != 'private' or
                update.from_user is not None and
                update.chat['id'] != update.from_user['id']):
            return

        state_key = 'user:{}:state'.format(update.from_user['id'])

        if update.text is not None:
            state = self.redis.get(state_key)
            if state == 'go':
                text = 'Договорились.'
                self.redis.delete(state_key)
                yield self.api.send_message(update.chat['id'], text)

                event_id = self.redis.incr('event:id')
                event_key = 'event:{}:text'.format(event_id)
                event_text = update.text
                self.redis.set(event_key, event_text)

                user_key = 'user:{}'.format(update.from_user['id'])
                self.redis.set(user_key, json.dumps(update.from_user))

                participants_key = 'event:{}:participants'.format(event_id)
                self.redis.sadd(participants_key, update.from_user['id'])

                participants = self.redis.smembers(participants_key)
                if participants:
                    participants = self.redis.mget(
                        map(lambda id: 'user:{}'.format(id), participants)
                    )
                text = render_event_message(event_id, event_text, participants)
                yield self.api.send_message(
                    update.chat['id'], text,
                    parse_mode='HTML',
                    reply_markup={
                        'inline_keyboard': get_event_keyboard(event_id, True),
                    },
                )


class EventCallbackQueryHandler(UpdateHandler):
    """Pub event callback query update handler."""

    @gen.coroutine
    def handle(self, update):
        if update.data is None:
            return

        changed = False
        action = update.data.split(':')
        if (action[0] == 'event_add'):
            try:
                event_id = int(action[1])
            except (IndexError, ValueError):
                pass
            else:
                user_key = 'user:{}'.format(update.from_user['id'])
                self.redis.set(user_key, json.dumps(update.from_user))
                participants_key = 'event:{}:participants'.format(event_id)
                changed = self.redis.sadd(participants_key,
                                          update.from_user['id'])
        elif (action[0] == 'event_del'):
            try:
                event_id = int(action[1])
            except (IndexError, ValueError):
                pass
            else:
                participants_key = 'event:{}:participants'.format(event_id)
                changed = self.redis.srem(participants_key,
                                          update.from_user['id'])

        if changed:
            event_key = 'event:{}:text'.format(event_id)
            event_text = self.redis.get(event_key)
            participants = self.redis.smembers(participants_key)
            if participants:
                participants = self.redis.mget(
                    map(lambda id: 'user:{}'.format(id), participants)
                )
            text = render_event_message(event_id, event_text, participants)
            yield self.api.edit_message_text(
                text,
                message=update.message,
                inline_message_id=update.inline_message_id,
                parse_mode='HTML',
                reply_markup={
                    'inline_keyboard': get_event_keyboard(
                        event_id, update.message is not None
                    ),
                },
            )


class EventInlineQueryHandler(UpdateHandler):
    """Pub event inline query update handler."""

    @gen.coroutine
    def handle(self, update):
        try:
            event_id = int(update.query)
        except ValueError:
            pass
        else:
            event_key = 'event:{}:text'.format(event_id)
            event_text = self.redis.get(event_key)
            if event_text:
                participants_key = 'event:{}:participants'.format(event_id)
                participants = self.redis.smembers(participants_key)
                if participants:
                    participants = self.redis.mget(
                        map(lambda id: 'user:{}'.format(id), participants)
                    )
                text = render_event_message(event_id, event_text, participants)
                yield self.api.answer_inline_query(
                    update.id,
                    [
                        {
                            'type': 'contact',
                            'id': str(event_id),
                            'phone_number': '(id: {})'.format(event_id),
                            'first_name': event_text,
                            'input_message_content': {
                                'message_text': text,
                                'parse_mode': 'HTML',
                            },
                            'reply_markup': {
                                'inline_keyboard': get_event_keyboard(
                                    event_id
                                ),
                            },
                        },
                    ],
                )
