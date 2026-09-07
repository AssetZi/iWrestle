"""Signing and field translation for the CloudKit REST backend."""
import base64
import hashlib
import json
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from iwpipe import ckws


@pytest.fixture(scope="module")
def key(tmp_path_factory):
    path = tmp_path_factory.mktemp("secrets") / "k.pem"
    private = ec.generate_private_key(ec.SECP256R1())
    path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    return path


def test_key_loads_and_signature_verifies(key):
    private = ckws.load_key(key)
    date, body = "2026-01-25T22:15:43Z", b'{"a":1}'
    path = "/database/1/iCloud.x/development/public/records/modify"
    signature = ckws.sign(private, date, body, path)

    message = f"{date}:{ckws.body_hash(body)}:{path}".encode()
    private.public_key().verify(
        base64.b64decode(signature), message, ec.ECDSA(hashes.SHA256())
    )


def test_body_hash_is_base64_sha256():
    assert ckws.body_hash(b"hello") == base64.b64encode(
        hashlib.sha256(b"hello").digest()
    ).decode()


def test_date_has_no_fraction_and_ends_in_z():
    stamp = ckws.iso_now()
    assert stamp.endswith("Z") and "." not in stamp
    datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")


def test_subpath_shape():
    assert ckws.subpath("iCloud.x", "production", "records/modify") == (
        "/database/1/iCloud.x/production/public/records/modify"
    )


CKTOOL_FIELDS = {
    "name": {"type": "stringType", "value": "Interstate Classic"},
    "date": {"type": "timestampType", "value": "2026-10-17T16:00:00Z"},
    "location": {"type": "locationType", "value": {"latitude": 41.2, "longitude": -79.4}},
    "userID": {"type": "referenceType", "value": {"recordName": "_abc", "action": "NONE"}},
    "ageGroups": {"type": "stringListType", "value": ["Youth", "Jr High"]},
    "logo": {"type": "assetType", "value": "LOGO"},
}


def test_field_translation():
    receipt = {"fileChecksum": "c", "size": 10, "receipt": "r"}
    out = ckws.to_ckws_fields(CKTOOL_FIELDS, {"LOGO": receipt})
    assert out["name"] == {"value": "Interstate Classic"}
    assert out["ageGroups"] == {"value": ["Youth", "Jr High"]}
    assert out["location"]["value"]["latitude"] == 41.2
    assert out["userID"]["value"]["recordName"] == "_abc"
    assert out["logo"] == {"value": receipt}
    # 2026-10-17T16:00:00Z in milliseconds
    expected = int(datetime(2026, 10, 17, 16, tzinfo=timezone.utc).timestamp() * 1000)
    assert out["date"] == {"value": expected}


def test_an_unuploaded_asset_is_an_error():
    with pytest.raises(ckws.CKWSError):
        ckws.to_ckws_fields(CKTOOL_FIELDS, {})


def test_post_sends_the_three_signed_headers(key, monkeypatch):
    sent = {}

    class Response:
        status_code = 200
        text = "{}"
        def json(self):
            return {"ok": True}

    class Session:
        def post(self, url, data=None, headers=None, timeout=None):
            sent.update(url=url, data=data, headers=headers)
            return Response()

    client = ckws.Client(key, "KEYID", "iCloud.x", "development", session=Session())
    client.post("records/modify", {"operations": []})
    assert sent["url"].startswith("https://api.apple-cloudkit.com/database/1/iCloud.x/development/public/")
    assert sent["headers"]["X-Apple-CloudKit-Request-KeyID"] == "KEYID"
    assert sent["headers"]["X-Apple-CloudKit-Request-SignatureV1"]
    assert json.loads(sent["data"]) == {"operations": []}


def test_delete_quotes_the_change_tag_and_tolerates_a_missing_record(key):
    calls = []

    class Response:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload
            self.text = json.dumps(payload)
        def json(self):
            return self._payload

    class Session:
        def __init__(self, lookup):
            self.lookup = lookup
        def post(self, url, data=None, headers=None, timeout=None):
            body = json.loads(data)
            calls.append((url.rsplit("/", 1)[-1], body))
            if url.endswith("lookup"):
                return Response({"records": [self.lookup]})
            return Response({"records": [{"recordName": "R1"}]})

    client = ckws.Client(key, "K", "iCloud.x", "development",
                         session=Session({"recordName": "R1", "recordChangeTag": "tag7"}))
    client.delete_record("R1")
    assert calls[0][0] == "lookup"
    assert calls[1][1]["operations"][0]["record"]["recordChangeTag"] == "tag7"

    calls.clear()
    gone = ckws.Client(key, "K", "iCloud.x", "development",
                       session=Session({"serverErrorCode": "NOT_FOUND"}))
    gone.delete_record("R9")
    assert [c[0] for c in calls] == ["lookup"]


def test_keys_are_chosen_per_environment(monkeypatch):
    """A development key gets a 401 in production, so each has its own id."""
    from iwpipe import cktool, config

    monkeypatch.setattr(config, "CLOUDKIT_KEY_ID", "DEV")
    monkeypatch.setattr(config, "CLOUDKIT_KEY_ID_PRODUCTION", "PROD")
    assert config.cloudkit_key_id("development") == "DEV"
    assert config.cloudkit_key_id("production") == "PROD"

    monkeypatch.setattr(config, "CLOUDKIT_KEY_ID_PRODUCTION", "")
    assert cktool.rest_client("production") is None
    assert "cktool" in cktool.backend_name("production")


def test_a_create_that_errors_after_commit_is_adopted_not_duplicated(key, monkeypatch):
    from iwpipe import cktool

    class Client:
        def __init__(self):
            self.created = 0
        def upload_asset(self, rt, field, path):
            return {"receipt": field}
        def create_record(self, rt, fields):
            self.created += 1
            raise ckws.CKWSError("records/modify failed (504): gateway timeout")
        def find_record(self, rt, name, day):
            assert (name, day) == ("Interstate Classic", "2026-10-17")
            return "EXISTING1"

    client = Client()
    fields = {"name": {"type": "stringType", "value": "Interstate Classic"},
              "date": {"type": "timestampType", "value": "2026-10-17T16:00:00Z"},
              "logo": {"type": "assetType", "value": "LOGO"},
              "flyer": {"type": "assetType", "value": "FLYER"}}
    tmp = __import__("pathlib").Path("/tmp")
    assert cktool.create_record_rest(client, fields, tmp / "a", tmp / "b") == "EXISTING1"
    assert client.created == 1
