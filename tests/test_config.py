import os
from unittest.mock import patch

import config


def test_api_disponible_false_sin_credenciales():
    assert config.API_DISPONIBLE is False


def test_api_disponible_true_con_credenciales():
    with patch.dict(os.environ, {
        "TICKETMASTER_API_KEY": "test_key",
        "TICKETMASTER_EVENT_ID": "test_id",
    }, clear=True):
        import importlib
        importlib.reload(config)
        assert config.API_DISPONIBLE is True
        importlib.reload(config)


def test_constantes_existen():
    assert config.API_DELAY == 20
    assert config.MAX_API_FAILURES == 3
    assert config.TELEGRAM_RETRIES == 3
    assert "ticketmaster.com" in config.API_BASE_URL
