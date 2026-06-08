from unittest.mock import patch

import config
from notificador import enviar_alerta


@patch("notificador.requests.get")
def test_enviar_alerta_exitoso(mock_get):
    mock_get.return_value.status_code = 200

    resultado = enviar_alerta("test mensaje")

    assert resultado is True
    mock_get.assert_called_once()


@patch("notificador.requests.get")
def test_enviar_alerta_falla_red(mock_get):
    from requests.exceptions import ConnectionError
    mock_get.side_effect = ConnectionError()

    resultado = enviar_alerta("test mensaje")

    assert resultado is False
    assert mock_get.call_count == config.TELEGRAM_RETRIES
