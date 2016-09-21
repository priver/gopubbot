from datetime import datetime

from tornado import gen


class Update(object):
    """Base class for Telegram Bot API updates."""

    update_type = None

    def __init__(self, update):
        self.update_id = update['update_id']


class MessageUpdate(Update):
    """Telegram Bot API message update."""

    update_type = 'message'

    def __init__(self, update):
        super().__init__(update)
        message = update['message']
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
        self.supergroup_chat_created = message.get('supergroup_chat_created',
                                                   None)
        self.channel_chat_created = message.get('channel_chat_created', None)
        self.migrate_to_chat_id = message.get('migrate_to_chat_id', None)
        self.migrate_from_chat_id = message.get('migrate_from_chat_id', None)
        self.pinned_message = message.get('pinned_message', None)


class BotCommandUpdate(MessageUpdate):
    """Telegram Bot API message update starting with command."""

    update_type = 'bot_command'

    def __init__(self, update, entity):
        super().__init__(update)
        self.bot_command = self.text[:entity['length']]


class EditedMessageUpdate(MessageUpdate):
    """Telegram Bot API edited message update."""

    update_type = 'edited_message'


class InlineQueryUpdate(Update):
    """Telegram Bot API inline query update."""

    update_type = 'inline_query'

    def __init__(self, update):
        super().__init__(update)
        inline_query = update['inline_query']
        self.id = inline_query['id']
        self.from_user = inline_query['from']
        self.location = inline_query.get('location', None)
        self.query = inline_query['query']
        self.offset = inline_query['offset']


class ChosenInlineResultUpdate(Update):
    """Telegram Bot API chosen inline result update."""

    update_type = 'chosen_inline_result'

    def __init__(self, update):
        super().__init__(update)
        chosen_inline_result = update['chosen_inline_result']
        self.result_id = chosen_inline_result['result_id']
        self.from_user = chosen_inline_result['from']
        self.location = chosen_inline_result.get('location', None)
        self.inline_message_id = chosen_inline_result.get('inline_message_id',
                                                          None)
        self.query = chosen_inline_result['query']


class CallbackQueryUpdate(Update):
    """Telegram Bot API callback query update."""

    update_type = 'callback_query'

    def __init__(self, update):
        super().__init__(update)
        callback_query = update['callback_query']
        self.id = callback_query['id']
        self.from_user = callback_query['from']
        self.message = callback_query.get('message', None)
        self.inline_message_id = callback_query.get('inline_message_id', None)
        self.data = callback_query.get('data', None)


class UpdateHandlerSpec(object):
    """Update handler spec."""

    def __init__(self, spec):
        self._handler = None
        if isinstance(spec, (list, tuple)):
            assert len(spec) == 2
            self._patterns, self._handler_class = spec
            if isinstance(self._patterns, str):
                self._patterns = [self._patterns]
        else:
            self._patterns = None
            self._handler_class = spec

    @property
    def patterns(self):
        return self._patterns

    @property
    def handler_class(self):
        return self._handler_class

    @property
    def handler(self):
        return self._handler

    def init_handler(self, *args, **kwargs):
        self._handler = self._handler_class(*args, **kwargs)


class UpdateDispatcher(object):
    """Update handlers dispatcher."""

    def __init__(self, update_handlers):
        self.handlers = update_handlers

    @gen.coroutine
    def dispatch(self, update_data):
        if 'message' in update_data:
            if ('text' in update_data['message'] and
                    'entities' in update_data['message']):
                for entity in update_data['message']['entities']:
                    if (entity['type'] == 'bot_command' and
                            entity['offset'] == 0):
                        update = BotCommandUpdate(update_data, entity)
                        yield self.find_bot_command_handlers(update)
                        return
            update = MessageUpdate(update_data)
            yield self.find_message_handlers(update)

        elif 'edited_message' in update_data:
            update = EditedMessageUpdate(update_data)
            yield self.find_edited_message_handlers(update)

        elif 'inline_query' in update_data:
            update = InlineQueryUpdate(update_data)
            yield self.find_inline_query_handlers(update)

        elif 'chosen_inline_result' in update_data:
            update = ChosenInlineResultUpdate(update_data)
            yield self.find_chosen_inline_result_handlers(update)

        elif 'callback_query' in update_data:
            update = CallbackQueryUpdate(update_data)
            yield self.find_callback_query_handlers(update)

    @gen.coroutine
    def find_message_handlers(self, update):
        handlers = self.handlers['message']
        yield [spec.handler.handle(update) for spec in handlers]

    @gen.coroutine
    def find_bot_command_handlers(self, update):
        for spec in self.handlers['bot_command']:
            if spec.patterns is None:
                yield spec.handler.handle(update)
            elif update.bot_command in spec.patterns:
                yield spec.handler.handle(update)

    @gen.coroutine
    def find_inline_query_handlers(self, update):
        handlers = self.handlers['inline_query']
        yield [spec.handler.handle(update) for spec in handlers]

    @gen.coroutine
    def find_chosen_inline_result_handlers(self, update):
        handlers = self.handlers['chosen_inline_result']
        yield [spec.handler.handle(update) for spec in handlers]

    @gen.coroutine
    def find_callback_query_handlers(self, update):
        handlers = self.handlers['callback_query']
        yield [spec.handler.handle(update) for spec in handlers]


class UpdateHandler(object):
    """Base class for Telegram Bot API update handlers."""

    def __init__(self, api, redis):
        self.api = api
        self.redis = redis

    @gen.coroutine
    def handle(self, update):
        raise NotImplementedError
