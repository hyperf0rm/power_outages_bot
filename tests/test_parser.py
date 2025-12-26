from bot.parser import Parser

MOCK_HTML = """
<html>
    <body>
        <p>27 декабря текущего года:</p>
        <p>дома 2-22 по ул. Бабаяна,</p>
        <p>улице Тиграняна,</p>
        <p>село Шенаван,</p>
        <p>28 декабря текущего года:</p>
        <p>дом 5 по ул. Азатутяна,</p>
        <p>частные дома в селе Ахпрадзор,</p>
        <p>село Шенаван,</p>
    </body>
</html>
            """

MOCK_EMPTY_HTML = """
<html>
    <body>
    </body>
</html>
                  """

MOCK_URL = "https://test.com/"


def test_parse_website_success(requests_mock):
    requests_mock.get(MOCK_URL, text=MOCK_HTML)
    parser = Parser()
    result = parser.parse_website()

    assert result
    assert "27 декабря текущего года:" in result
    assert "дома 2-22 по ул. Бабаяна" in result["27 декабря текущего года:"]
    assert "улице Тиграняна" in result["27 декабря текущего года:"]
    assert "28 декабря текущего года:" in result
    assert "дом 5 по ул. Азатутяна" in result["28 декабря текущего года:"]
    assert ("частные дома в селе Ахпрадзор"
            in result["28 декабря текущего года:"])
    assert ("село Шенаван" in result["27 декабря текущего года:"]
            and result["28 декабря текущего года:"])


def test_parse_website_empty_response(requests_mock):
    requests_mock.get(MOCK_URL, text=MOCK_EMPTY_HTML)
    parser = Parser()
    result = parser.parse_website()

    assert result == {}


def test_parse_website_http_error(requests_mock):
    requests_mock.get(MOCK_URL, status_code=500)
    parser = Parser()
    result = parser.parse_website()

    assert not result
