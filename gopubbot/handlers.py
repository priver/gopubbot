import simplejson as json
from tornado import gen


def render_event_message(event_text, participants):
    text = '\U0001F37A *{}*!\n\n'.format(event_text)
    if participants:
        users = []
        for participant in participants:
            user = json.loads(participant)
            if 'username' in user:
                users.append('@' + user['username'])
            else:
                name = user['first_name']
                if 'last_name' in user:
                    name += ' ' + user['last_name']
                users.append(name)
        text += 'Идут ({}):\n{}\n'.format(len(users), ', '.join(users))
    else:
        text += 'Пока никто не идет.\n'

    return text


@gen.coroutine
def handle_message(update, api, redis):
    message = update['message']
    command = None
    if (message['chat']['type'] != 'private' or
            message['chat']['id'] != message['from']['id']):
        return

    state_key = 'user:{}:state'.format(message['from']['id'])

    if 'entities' in message:
        for entity in message['entities']:
            if entity['type'] == 'bot_command' and entity['offset'] == 0:
                command = message['text'][:entity['length']]
    if command == '/go':
        state = redis.set(state_key, 'go')
        text = 'Куда и во сколько?'
        yield api.send_message(update['message']['chat']['id'], text)
    else:
        state = redis.get(state_key)
        if state == 'go':
            text = 'Договорились.'
            redis.delete(state_key)
            yield api.send_message(update['message']['chat']['id'], text)

            event_id = redis.incr('event:id')
            event_key = 'event:{}:text'.format(event_id)
            event_text = message['text']
            redis.set(event_key, event_text)

            user_key = 'user:{}'.format(message['from']['id'])
            redis.set(user_key, json.dumps(message['from']))

            participants_key = 'event:{}:participants'.format(event_id)
            redis.sadd(participants_key, message['from']['id'])

            participants = redis.smembers(participants_key)
            if participants:
                participants = redis.mget(
                    map(lambda id: 'user:{}'.format(id), participants)
                )
            text = render_event_message(event_text, participants)
            yield api.send_message(
                message['chat']['id'], text,
                parse_mode='Markdown',
                reply_markup={
                    'inline_keyboard': [
                        [
                            {
                                'text': 'Я иду!',
                                'callback_data': 'event_add:{}'.format(event_id)
                            },
                            {
                                'text': 'Не пойду',
                                'callback_data': 'event_del:{}'.format(event_id)
                            },
                        ],
                    ],
                })


@gen.coroutine
def handle_callback_query(update, api, redis):
    callback_query = update['callback_query']
    if ('data' in callback_query):
        changed = False
        action = callback_query['data'].split(':')
        if (action[0] == 'event_add'):
            try:
                event_id = int(action[1])
            except (IndexError, ValueError):
                pass
            else:
                user_key = 'user:{}'.format(callback_query['from']['id'])
                redis.set(user_key, json.dumps(callback_query['from']))
                participants_key = 'event:{}:participants'.format(event_id)
                changed = redis.sadd(participants_key,
                                     callback_query['from']['id'])
        elif (action[0] == 'event_del'):
            try:
                event_id = int(action[1])
            except (IndexError, ValueError):
                pass
            else:
                participants_key = 'event:{}:participants'.format(event_id)
                changed = redis.srem(participants_key,
                                     callback_query['from']['id'])
        if changed:
            event_key = 'event:{}:text'.format(event_id)
            event_text = redis.get(event_key)
            participants = redis.smembers(participants_key)
            if participants:
                participants = redis.mget(
                    map(lambda id: 'user:{}'.format(id), participants)
                )
            text = render_event_message(event_text, participants)
            yield api.edit_message_text(
                callback_query['message']['chat']['id'],
                callback_query['message']['message_id'],
                text,
                parse_mode='Markdown',
                reply_markup={
                    'inline_keyboard': [
                        [
                            {
                                'text': 'Я иду!',
                                'callback_data': 'event_add:{}'.format(event_id)
                            },
                            {
                                'text': 'Не пойду',
                                'callback_data': 'event_del:{}'.format(event_id)
                            },
                        ],
                    ],
                })
