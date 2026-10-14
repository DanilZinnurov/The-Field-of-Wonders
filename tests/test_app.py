import pytest
from app import app, init_game


@pytest.fixture
def test_dict():
    """Тестовый словарь — изолирует тесты от реальных данных"""
    return {
        'TEST': 'Тестовое слово для проверки',
        'FALSE': 'Логическое значение',
        'NONE': 'Пустой объект в Python',
    }


@pytest.fixture(autouse=True)
def patch_dict(monkeypatch, test_dict):
    """Автоматически подменяет _dict во всех тестах"""
    import app as app_module
    monkeypatch.setattr(app_module, '_dict', test_dict)


@pytest.fixture
def client():
    """Создаёт тестового клиента Flask"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret'
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def client_with_game(client):
    """Клиент с инициализированной игрой (слово TEST)"""
    with client.session_transaction() as sess:
        sess['secret'] = 'TEST'
        sess['mask'] = ['*', '*', '*', '*']
        sess['guessed'] = []
        sess['wrong'] = []
        sess['message'] = 'Угадайте слово!'
        sess['won'] = False
    return client


# ==================== Тесты инициализации ====================

def test_init_game_creates_session(test_dict):
    """init_game() должна корректно заполнить session"""
    with app.test_request_context():
        from flask import session
        init_game()
        assert 'secret' in session
        assert 'mask' in session
        assert session['secret'] in test_dict
        assert len(session['mask']) == len(session['secret'])
        assert all(c == '*' for c in session['mask'])
        assert session['guessed'] == []
        assert session['wrong'] == []
        assert session['won'] is False


# ==================== Тесты главной страницы ====================

def test_index_initializes_game(client):
    """При первом заходе игра должна автоматически инициализироваться"""
    response = client.get('/')
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert 'secret' in sess
        assert 'mask' in sess


def test_index_renders_template(client_with_game, test_dict):
    """Главная страница должна отображать маску и описание"""
    response = client_with_game.get('/')
    assert response.status_code == 200
    data = response.data.decode('utf-8')
    # В HTML должна быть маска из 4 звёзд (слово TEST)
    assert data.count('letter-box hidden') == 4
    # Должно быть описание слова TEST из тестового словаря
    assert test_dict['TEST'] in data


# ==================== Тесты валидации ввода ====================

def test_guess_empty_letter(client_with_game):
    """Пустой ввод должен отклоняться"""
    client_with_game.post('/guess', data={'letter': ''}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert '⚠️' in sess['message']


def test_guess_multiple_letters(client_with_game):
    """Ввод нескольких символов должен отклоняться"""
    client_with_game.post('/guess', data={'letter': 'AB'}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert '⚠️' in sess['message']


def test_guess_non_alpha(client_with_game):
    """Цифры и спецсимволы должны отклоняться"""
    client_with_game.post('/guess', data={'letter': '1'}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert '⚠️' in sess['message']


def test_guess_missing_field(client_with_game):
    """Отсутствие поля letter не должно ломать приложение"""
    response = client_with_game.post('/guess', data={}, follow_redirects=True)
    assert response.status_code == 200


# ==================== Тесты игровой логики ====================

def test_guess_correct_letter(client_with_game):
    """Правильная буква должна открываться в маске"""
    client_with_game.post('/guess', data={'letter': 'T'}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        # Слово TEST: T на позициях 0 и 3
        assert sess['mask'][0] == 'T'
        assert sess['mask'][3] == 'T'
        assert 'T' in sess['guessed']
        assert '✅' in sess['message']


def test_guess_wrong_letter(client_with_game):
    """Неправильная буква должна попадать в список промахов"""
    client_with_game.post('/guess', data={'letter': 'Z'}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert 'Z' in sess['wrong']
        assert '❌' in sess['message']


def test_guess_case_insensitive(client_with_game):
    """Регистр буквы не должен иметь значения"""
    client_with_game.post('/guess', data={'letter': 't'}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert 'T' in sess['guessed']


def test_guess_duplicate_letter(client_with_game):
    """Повторный ввод буквы должен отклоняться"""
    client_with_game.post('/guess', data={'letter': 'T'})
    client_with_game.post('/guess', data={'letter': 'T'}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert sess['guessed'].count('T') == 1
        assert 'уже называли' in sess['message']


def test_guess_win_condition(client_with_game):
    """При полном открытии слова должна срабатывать победа"""
    # Последовательно открываем все буквы слова TEST
    for letter in ['T', 'E', 'S']:
        client_with_game.post('/guess', data={'letter': letter})

    with client_with_game.session_transaction() as sess:
        assert sess['won'] is True
        assert '🏆' in sess['message']
        assert '*' not in sess['mask']


def test_win_disables_input(client_with_game):
    """После победы форма ввода должна исчезать"""
    for letter in ['T', 'E', 'S']:
        client_with_game.post('/guess', data={'letter': letter})

    response = client_with_game.get('/')
    data = response.data.decode('utf-8')
    assert 'Крутить барабан' not in data
    assert 'Новая игра' in data


# ==================== Тесты сброса игры ====================

def test_reset_creates_new_game(client_with_game):
    """Сброс должен создавать новую игру"""
    response = client_with_game.get('/reset', follow_redirects=True)
    assert response.status_code == 200

    with client_with_game.session_transaction() as sess:
        assert sess['guessed'] == []
        assert sess['wrong'] == []
        assert sess['won'] is False
        assert '*' in sess['mask']


# ==================== Тесты граничных случаев ====================

def test_whitespace_only_input(client_with_game):
    """Пробелы должны отклоняться"""
    client_with_game.post('/guess', data={'letter': '   '}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert '⚠️' in sess['message']


def test_guess_with_leading_trailing_spaces(client_with_game):
    """Пробелы вокруг буквы должны обрезаться"""
    client_with_game.post('/guess', data={'letter': '  T  '}, follow_redirects=True)
    with client_with_game.session_transaction() as sess:
        assert 'T' in sess['guessed']