from datetime import datetime

from tornado import gen


class UpdateHandler(object):
    """Base class for Telegram Bot API update handlers."""

    update_types = ['message', 'edited_message', 'inline_query',
                    'chosen_inline_result', 'callback_query']

    def __init__(self, api, redis):
        self.api = api
        self.redis = redis

    @gen.coroutine
    def dispatch(self, update):
        for update_type in self.update_types:
            if update_type in update:
                try:
                    handle = getattr(self, 'handle_{0}'.format(update_type))
                except AttributeError:
                    pass
                else:
                    populate_data = getattr(self, 'populate_{0}'.format(update_type))
                    populate_data(update)
                    yield handle()
                break

    def populate_message(self, update):
        message = update['message']
        self.update_id = update['update_id']
        self.message_id = message['message_id']
        self.from_user = message.get('from', None)
        self.date = datetime.fromtimestamp(message['date'])
        self.chat = message['chat']
        self.forward_from = message.get('forward_from', None)
        self.forward_from_chat = message.get('forward_from_chat', None)
        try:
            self.forward_date = message['forward_date']
        except (KeyError, TypeError):
            self.forward_date = None
        self.reply_to_message = message.get('reply_to_message', None)
        try:
            self.edit_date = message['edit_date']
        except (KeyError, TypeError):
            self.edit_date = None
        self.text = message.get('text', None)
        self.entities = message.get('entities', None)
        self.audio = message.get('audio', None)
        self.document = message.get('document', None)
        self.photo = message.get('photo', None)
        self.sticker = message.get('sticker', None)
        self.video = message.get('video', None)
        self.voice = message.get('voice', None)
        self.caption = message.get('caption', None)
        self.contact = message.get('contact', None)
        self.location = message.get('location', None)
        self.venue = message.get('venue', None)
        self.new_chat_member = message.get('new_chat_member', None)
        self.left_chat_member = message.get('left_chat_member', None)
        self.new_chat_title = message.get('new_chat_title', None)
        self.new_chat_photo = message.get('new_chat_photo', None)
        self.delete_chat_photo = message.get('delete_chat_photo', None)
        self.group_chat_created = message.get('group_chat_created', None)
        self.supergroup_chat_created = message.get('supergroup_chat_created', None)
        self.channel_chat_created = message.get('channel_chat_created', None)
        self.migrate_to_chat_id = message.get('migrate_to_chat_id', None)
        self.migrate_from_chat_id = message.get('migrate_from_chat_id', None)
        self.pinned_message = message.get('pinned_message', None)

        self.bot_command = None
        if self.entities is not None and self.text is not None:
            for entity in self.entities:
                if entity['type'] == 'bot_command' and entity['offset'] == 0:
                    self.bot_command = self.text[:entity['length']]
                break

    def populate_edited_message(self, update):
        update['message'] = update['edited_message']
        self.populate_message(self, update)

    def populate_inline_query(self, update):
        inline_query = update['inline_query']
        self.update_id = update['update_id']
        self.id = inline_query['id']
        self.from_user = inline_query['from']
        self.location = inline_query.get('location', None)
        self.query = inline_query['query']
        self.offset = inline_query['offset']

    def populate_chosen_inline_result(self, update):
        chosen_inline_result = update['chosen_inline_result']
        self.update_id = update['update_id']
        self.result_id = chosen_inline_result['result_id']
        self.from_user = chosen_inline_result['from']
        self.location = chosen_inline_result.get('location', None)
        self.inline_message_id = chosen_inline_result.get('inline_message_id', None)
        self.query = chosen_inline_result['query']

    def populate_callback_query(self, update):
        callback_query = update['callback_query']
        self.update_id = update['update_id']
        self.id = callback_query['id']
        self.from_user = callback_query['from']
        self.message = callback_query.get('message', None)
        self.inline_message_id = callback_query.get('inline_message_id', None)
        self.data = callback_query.get('data', None)
