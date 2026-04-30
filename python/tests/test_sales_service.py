import io
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import FAKE_ORG_ID


def _fake_audio(length_seconds: float):
    meta = MagicMock()
    meta.info.length = length_seconds
    return meta


def _upload(client, filename="test.mp3"):
    return client.post(
        "/sales/calls/upload",
        files={
            "audio_file": (
                filename,
                io.BytesIO(b"audio"),
                "audio/mpeg",
            )
        },
    )


def test_upload_rejects_malformed_file(client, mock_db):
    with patch("api.sales_service.mutagen.File", return_value=None):
        response = _upload(client)

    assert response.status_code == 400


def test_upload_rejects_file_under_60s(client, mock_db):
    with patch(
        "api.sales_service.mutagen.File",
        return_value=_fake_audio(length_seconds=45),
    ):
        response = _upload(client)

    assert response.status_code == 400


def test_upload_blocked_when_quota_exceeded(client, mock_db):
    mock_db.get_rows.side_effect = lambda table, **kw: (
        [{"minutes_analysed": 240}]
        if table == "organizations"
        else [{"plan": "free"}]
    )
    with patch(
        "api.sales_service.mutagen.File",
        return_value=_fake_audio(length_seconds=90),
    ):
        response = _upload(client)

    assert response.status_code == 402

