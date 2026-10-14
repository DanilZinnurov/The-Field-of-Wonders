import random
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
# Секретный ключ необходим для работы сессий
app.secret_key = 'super_secret_key_for_field_of_miracles_123'

# Расширенный словарь для более интересной игры
_dict = {
    'FALSE': 'Логическое значение',
    'NONE': 'Пустой объект в Python',
    'LIST': 'Изменяемая упорядоченная коллекция',
    'TUPLE': 'Неизменяемая упорядоченная коллекция',
    'DICT': 'Коллекция пар ключ-значение',
    'DEF': 'Ключевое слово для создания функции',
    'CLASS': 'Чертеж для создания объектов',
    'IMPORT': 'Подключение внешних модулей'
}

def init_game():
    """Инициализирует новую игру и сохраняет состояние в сессию"""
    keys = list(_dict.keys())
    secret = random.choice(keys)
    session['secret'] = secret
    session['mask'] = ['*'] * len(secret)
    session['guessed'] = []      # Угаданные буквы
    session['wrong'] = []        # Неугаданные буквы
    session['message'] = 'Угадайте слово!'
    session['won'] = False

@app.route('/')
def index():
    """Главная страница: отображает текущее состояние игры"""
    if 'secret' not in session:
        init_game()

    # Формируем строку из маски для отображения
    mask_str = ''.join(session['mask'])
    description = _dict[session['secret']]

    return render_template('index.html',
                           mask=mask_str,
                           description=description,
                           guessed=session['guessed'],
                           wrong=session['wrong'],
                           message=session['message'],
                           won=session['won'])

@app.route('/guess', methods=['POST'])
def guess():
    """Обработка введенной буквы"""
    letter = request.form.get('letter', '').upper().strip()

    # Валидация ввода
    if not letter or len(letter) != 1 or not letter.isalpha():
        session['message'] = '⚠️ Введите одну букву!'
        return redirect(url_for('index'))

    # Проверка на повтор
    if letter in session['guessed'] or letter in session['wrong']:
        session['message'] = '⚠️ Вы уже называли эту букву!'
        return redirect(url_for('index'))

    secret = session['secret']
    mask = session['mask']

    # Логика проверки буквы
    if letter in secret:
        for i, char in enumerate(secret):
            if char == letter:
                mask[i] = letter
        session['guessed'].append(letter)
        session['message'] = '✅ Есть такая буква!'
    else:
        session['wrong'].append(letter)
        session['message'] = '❌ Нет такой буквы...'

    # Проверка на победу
    if '*' not in mask:
        session['won'] = True
        session['message'] = f'🏆 Поздравляем! Вы угадали слово: {secret}'

    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    """Сброс игры"""
    init_game()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)