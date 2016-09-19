import html

import simplejson as json
from tornado import gen

from .bot.update import UpdateHandler


class PubHandler(UpdateHandler):
    """Pub update handler."""

    @gen.coroutine
    def handle_message(self):
        if (self.chat['type'] != 'private' or
                self.from_user is not None and
                self.chat['id'] != self.from_user['id']):
            return

        state_key = 'user:{}:state'.format(self.from_user['id'])

        if self.bot_command == '/go':
            state = self.redis.set(state_key, 'go')
            text = 'Куда и во сколько?'
            yield self.api.send_message(self.chat['id'], text)
        elif self.text is not None:
            state = self.redis.get(state_key)
            if state == 'go':
                text = 'Договорились.'
                self.redis.delete(state_key)
                yield self.api.send_message(self.chat['id'], text)

                event_id = self.redis.incr('event:id')
                event_key = 'event:{}:text'.format(event_id)
                event_text = self.text
                self.redis.set(event_key, event_text)

                user_key = 'user:{}'.format(self.from_user['id'])
                self.redis.set(user_key, json.dumps(self.from_user))

                participants_key = 'event:{}:participants'.format(event_id)
                self.redis.sadd(participants_key, self.from_user['id'])

                participants = self.redis.smembers(participants_key)
                if participants:
                    participants = self.redis.mget(
                        map(lambda id: 'user:{}'.format(id), participants)
                    )
                text = self.render_event_message(event_id, event_text, participants)
                yield self.api.send_message(
                    self.chat['id'], text,
                    parse_mode='HTML',
                    reply_markup={
                        'inline_keyboard': self.render_event_keyboard(event_id, True),
                    },
                )

    @gen.coroutine
    def handle_callback_query(self):
        if self.data is None:
            return

        changed = False
        action = self.data.split(':')
        if (action[0] == 'event_add'):
            try:
                event_id = int(action[1])
            except (IndexError, ValueError):
                pass
            else:
                user_key = 'user:{}'.format(self.from_user['id'])
                self.redis.set(user_key, json.dumps(self.from_user))
                participants_key = 'event:{}:participants'.format(event_id)
                changed = self.redis.sadd(participants_key, self.from_user['id'])
        elif (action[0] == 'event_del'):
            try:
                event_id = int(action[1])
            except (IndexError, ValueError):
                pass
            else:
                participants_key = 'event:{}:participants'.format(event_id)
                changed = self.redis.srem(participants_key, self.from_user['id'])

        if changed:
            event_key = 'event:{}:text'.format(event_id)
            event_text = self.redis.get(event_key)
            participants = self.redis.smembers(participants_key)
            if participants:
                participants = self.redis.mget(
                    map(lambda id: 'user:{}'.format(id), participants)
                )
            text = self.render_event_message(event_id, event_text, participants)
            edit_kwargs = {
                'parse_mode': 'HTML',
                'reply_markup': {
                    'inline_keyboard': self.render_event_keyboard(
                        event_id,
                        self.message is not None
                    ),
                },
            }
            if self.inline_message_id is not None:
                edit_kwargs.update({
                    'inline_message_id': self.inline_message_id,
                })
            else:
                edit_kwargs.update({
                    'chat_id': self.message['chat']['id'],
                    'message_id': self.message['message_id'],
                })
            yield self.api.edit_message_text(text, **edit_kwargs)

    @gen.coroutine
    def handle_inline_query(self):
        try:
            event_id = int(self.query)
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
                text = self.render_event_message(event_id, event_text, participants)
                yield self.api.answer_inline_query(
                    self.id,
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
                                'inline_keyboard': self.render_event_keyboard(event_id),
                            },
                        },
                    ],
                )

    def render_event_message(self, event_id, event_text, participants):
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

    def render_event_keyboard(self, event_id, show_switch_query=False):
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
