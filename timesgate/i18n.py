"""Languages: on-screen words per language, and Ukrainian translations of the settings page and tray texts.

The source text is English (in the code and timesgate/ui/index.html); `[ui] language = "uk"` shows UK[text] instead.
A text missing from UK simply stays in English.
"""
LANGUAGES = ("en", "uk")

# Words drawn on the device screens. Weekdays are Monday first.
WORDS = {
    "en": {
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "today": "Today", "tomorrow": "Tomorrow", "now_until": "Now · until {}", "all_day": "all day",
        "task": "task", "undated_task": "Task", "overdue": "Overdue", "untitled": "(untitled)",
        "total": "Total", "inbox": "Inbox",
    },
    "uk": {
        "weekdays": ["Пон", "Вів", "Сер", "Чет", "П’ят", "Суб", "Нед"],
        "today": "Сьогодні", "tomorrow": "Завтра", "now_until": "Зараз · до {}", "all_day": "весь день",
        "task": "завдання", "undated_task": "Завдання", "overdue": "Прострочено", "untitled": "(без назви)",
        "total": "Усього", "inbox": "Вхідні",
    },
}

UK = {
    # tray
    "Settings": "Налаштування",
    "Refresh screens": "Оновити екрани",
    "Exit": "Вихід",
    # options every widget has
    "How often to refresh, seconds": "Як часто оновлювати, секунд",
    "Retry after an error, seconds (empty = same as every)": "Повтор після помилки, секунд (порожньо = як «every»)",
    "Refresh exactly on the interval boundary, e.g. at the start of a minute":
        "Оновлювати рівно на межі інтервалу, напр. на початку хвилини",
    # Google widgets
    "OAuth client (Desktop app), path relative to config.toml, a mask is fine":
        "OAuth-клієнт (Desktop app), шлях від config.toml, можна маску",
    "Created by the sign-in button on the System tab": "Створюється кнопкою «Увійти» на вкладці «Система»",
    # prices
    "Prices": "Ціни",
    "Latest Binance prices and 24 h change, up to 4 rows": "Останні ціни Binance і зміна за 24 год, до 4 рядків",
    "futures = USDⓈ-M perpetual futures, spot = spot": "futures — безстрокові ф'ючерси USDⓈ-M, spot — спот",
    "Quote currency": "Валюта котирування",
    "Tickers without the quote currency, 1–4": "Тікери без валюти котирування, 1–4",
    # chart
    "Chart": "Графік",
    "Binance candle closes, change in % and the last price": "Графік закриттів свічок Binance, зміна у % і остання ціна",
    "The full pair, e.g. BTCUSDT": "Пара повністю, напр. BTCUSDT",
    "Length of one candle": "Довжина однієї свічки",
    "Number of candles, 2–1000 (96 × 15m = a day)": "Кількість свічок, 2–1000 (96 × 15m = доба)",
    "Caption above the chart": "Підпис над графіком",
    # rates
    "Exchange rates": "Курси валют",
    "PrivatBank buy / sell to the hryvnia": "Купівля / продаж у ПриватБанку до гривні",
    "Currency codes, 1–2, e.g. USD, EUR": "Коди валют, 1–2, напр. USD, EUR",
    # clock
    "Clock": "Годинник",
    "24-hour time and the date with the weekday": "24-годинний час і дата з днем тижня",
    "The colon blinks (a 2-frame animation the device loops by itself)":
        "Двокрапка блимає (анімація з 2 кадрів, яку крутить сам пристрій)",
    "Show the date below the time": "Показувати дату під часом",
    "strftime format, e.g. %d.%m": "Формат strftime, напр. %d.%m",
    "7 names starting with Monday (empty = the language's own)":
        "7 назв, починаючи з понеділка (порожньо = як у вибраній мові)",
    "Size of the time digits, px": "Розмір цифр часу, px",
    "Size of the date, px": "Розмір дати, px",
    # text
    "Text": "Текст",
    "Static centred text": "Статичний текст по центру",
    "Several lines are fine": "Можна в кілька рядків",
    "Font size, px": "Розмір шрифту, px",
    "Cyrillic font from the theme (the default one has none)": "Шрифт з кирилицею з теми (стандартний її не має)",
    # weather
    "Weather": "Погода",
    "Temperature, sky, today's max/min and a 2-day forecast from Open-Meteo":
        "Температура, небо, денні макс./мін. і прогноз на 2 дні з Open-Meteo",
    "Name above the temperature (Latin letters: the default font has no Cyrillic)":
        "Назва над температурою (латиницею: стандартний шрифт без кирилиці)",
    "Latitude": "Широта",
    "Longitude": "Довгота",
    "Time zone, e.g. Europe/London": "Часовий пояс, напр. Europe/London",
    "Sky icon next to the temperature": "Іконка неба біля температури",
    "Tomorrow and the day after at the bottom: icon, max/min": "Унизу завтра й післязавтра: іконка, макс./мін.",
    # gmail
    "Unread mail: total and by label; shown only when it grows":
        "Непрочитані: усього й за мітками; показується, лише коли їх стало більше",
    "Label counted as Total: UNREAD = all unread mail, INBOX = the inbox only":
        "Мітка, яку рахує «Усього»: UNREAD — усі непрочитані, INBOX — лише вхідні",
    # calendar
    "Calendar": "Календар",
    "Google events and tasks: today's past events in grey, then the next ones":
        "Події й завдання Google: сьогоднішні минулі події сірим, далі найближчі",
    "Calendar id: primary = your main one, others are in Google Calendar settings":
        "Id календаря: primary — основний, інші в налаштуваннях Google Calendar",
    "Also open Google Tasks; undated ones last (needs a sign-in with the tasks permission)":
        "Показувати й невиконані завдання Google Tasks; без дати — в кінці (потрібен вхід із дозволом на завдання)",
    "Task list: @default = My Tasks": "Список завдань: @default — «Мої завдання»",
    "How many days ahead to look": "На скільки днів уперед шукати",
    "How many rows to show, 1–4": "Скільки рядків показати, 1–4",
    "How many of today's past events to keep on top in grey (less than count)":
        "Скільки сьогоднішніх минулих подій лишати зверху сірим (менше за count)",
    # settings page (timesgate/ui/index.html)
    'App not responding': 'Програма не відповідає',
    'Device online': 'Пристрій на зв’язку',
    'Device unreachable': 'Пристрій недоступний',
    'Unsaved changes': 'Є незбережені зміни',
    'Cancel': 'Скасувати',
    'Saving…': 'Зберігаю…',
    'Save': 'Зберегти',
    'Not saved.': 'Не збережено.',
    'Close': 'Закрити',
    'Device screens': 'Екрани пристрою',
    'Screen': 'Екран',
    'nothing sent yet': 'ще нічого не надіслано',
    'not configured': 'не налаштовано',
    'Widgets by priority: the screen shows the first one that has something to show now.': 'Віджети за пріоритетом: на екрані перший, якому зараз є що показати.',
    'Drag to change the priority': 'Перетягніть, щоб змінити пріоритет',
    'Up': 'Вище',
    'Down': 'Нижче',
    'Remove widget': 'Видалити віджет',
    'Options': 'Параметри',
    'Schedule': 'Розклад',
    'Unknown type': 'Невідомий тип',
    'Nothing on this screen. Add a widget and it appears on the device after saving.': 'На цьому екрані нічого немає. Додайте віджет — і він з’явиться на пристрої після збереження.',
    '+ Add widget': '+ Додати віджет',
    'Preview': 'Прев’ю',
    'Refresh': 'Оновити',
    'on the device': 'на пристрої',
    'nothing to show': 'нічого показати',
    'draft': 'чернетка',
    'Showing:': 'Показується:',
    'animation': 'анімація',
    'frames': 'кадри',
    'The preview takes fresh data from the internet and sends nothing to the device.': 'Прев’ю бере свіжі дані з інтернету й нічого не надсилає на пристрій.',
    'Connection': 'Підключення',
    'Times Gate local HTTP API.': 'Локальний HTTP API Times Gate.',
    'When the program stops': 'Коли програма зупиняється',
    'Command sent on tray Exit, Ctrl+C or closing the console. Not sent if the PC shuts down, sleeps or the process is killed.': 'Команда при виході з трею, Ctrl+C чи закритті консолі. Не надсилається, якщо комп’ютер вимкнувся, заснув або процес убито.',
    'Do nothing': 'Нічого не робити',
    'Switch on the built-in clock': 'Увімкнути вбудований годинник',
    'Custom command': 'Своя команда',
    'Clock face number': 'Номер циферблата',
    'Command as JSON': 'Команда у JSON',
    'needs an object with a "Command" field': 'потрібен об’єкт з полем "Command"',
    'Not applied:': 'Не застосовано:',
    'Colours': 'Кольори',
    'Shared by all screens.': 'Спільні для всіх екранів.',
    'Program': 'Програма',
    'Start with Windows': 'Запускати при вході в Windows',
    'No console window, with a tray icon. If you moved the folder, switch it on again.': 'Без вікна консолі, з іконкою в треї. Якщо перенесли папку — увімкніть ще раз.',
    'Windows only': 'лише Windows',
    'Autostart': 'Автозапуск',
    'Connected.': 'Підключено.',
    "There is a token, but it doesn't work: sign in again.": 'Токен є, але не працює — увійдіть ще раз.',
    'Not connected. Needs secrets/client_secret*.json and the API enabled in Google Cloud.': 'Не підключено. Потрібен secrets/client_secret*.json і увімкнений API в Google Cloud.',
    'Sign in again': 'Увійти знову',
    'Sign in': 'Увійти',
    'No Gmail or Calendar widget on any screen.': 'Віджетів Gmail чи Календаря немає на жодному екрані.',
    'Config:': 'Конфігурація:',
    'The previous version is kept as': 'Попередня версія зберігається як',
    'Log': 'Журнал',
    'The last 300 lines.': 'Останні 300 рядків.',
    'Empty.': 'Порожньо.',
    'hr': 'год',
    'min': 'хв',
    'Remove': 'Прибрати',
    'Reset to default': 'Повернути типове значення',
    'same as every': 'як every',
    'Type and press Enter': 'Введіть і натисніть Enter',
    'Background': 'Фон',
    'Main text': 'Основний текст',
    'Labels': 'Підписи',
    'Bottom line (time, date)': 'Нижній рядок (час, дата)',
    'Rise (chart line)': 'Ріст (лінія графіка)',
    'Fall': 'Падіння',
    'Fill under a rise': 'Заливка під ростом',
    'Fill under a fall': 'Заливка під падінням',
    'Font with Cyrillic (.ttf)': 'Шрифт із кирилицею (.ttf)',
    'Port': 'Порт',
    'API path': 'Шлях API',
    'Request timeout, seconds': 'Тайм-аут запиту, секунд',
    'JPEG quality, 1–100': 'Якість JPEG, 1–100',
    'Screens': 'Екрани',
    'Device': 'Пристрій',
    'Theme': 'Тема',
    'System': 'Система',
    'empty': 'порожньо',
    'every': 'кожні',
    's': 'с',
    'just now': 'щойно',
    'min ago': 'хв тому',
    'Device IP address': 'IP-адреса пристрою',
    'Log level': 'Рівень журналу',
    'Port of this page (after a program restart)': 'Порт цієї сторінки (після перезапуску програми)',
    'Language (screens and this page; tray after a restart)': 'Мова (екрани й ця сторінка; трей — після перезапуску)',
    'Saved. Screens are updating…': 'Збережено. Екрани оновлюються…',
    'Autostart on': 'Автозапуск увімкнено',
    'Autostart off': 'Автозапуск вимкнено',
    'A browser opened: sign in to Google and allow access': 'Відкрився браузер — увійдіть у Google і дозвольте доступ',
    'Could not load the config:': 'Не вдалося завантажити конфігурацію:',
}


def tr(text, lang):
    return UK.get(text, text) if lang == "uk" else text
