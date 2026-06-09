from unittest.mock import patch

import config
from reporte_wa import enviar_reporte_wa


@patch("reporte_wa.requests.post")
def test_enviar_reporte_exitoso(mock_post):
    mock_post.return_value.status_code = 200

    with patch.object(config, "OPENWA_DISPONIBLE", True):
        resultado = enviar_reporte_wa("test whatsapp")

    assert resultado is True
    mock_post.assert_called_once()


@patch("reporte_wa.requests.post")
def test_enviar_reporte_no_configurado(mock_post):
    with patch.object(config, "OPENWA_DISPONIBLE", False):
        resultado = enviar_reporte_wa("test whatsapp")

    assert resultado is False
    mock_post.assert_not_called()
