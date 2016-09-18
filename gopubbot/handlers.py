from tornado import gen


@gen.coroutine
def handle_message(api, update):
    print(update)
    message = 'Привет!'
    if (update['message']['from']['username']):
        message = 'Привет, @{}!'.format(update['message']['from']['username'])
    yield api.send_message(update['message']['chat']['id'], message)
