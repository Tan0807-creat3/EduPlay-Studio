import base64
import json
import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestFirebaseServiceAccountFernet(unittest.TestCase):
    def test_normalize_service_account_payload_accepts_json_and_base64(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        payload = json.dumps({"project_id": "demo-project"}, ensure_ascii=False)
        expected_b64 = base64.b64encode(payload.encode("utf-8")).decode("utf-8")

        self.assertEqual(svc._normalize_service_account_payload(payload), expected_b64)
        self.assertEqual(svc._normalize_service_account_payload(expected_b64), expected_b64)

    def test_read_service_account_b64_decrypts_fernet_from_env(self):
        from cryptography.fernet import Fernet

        from eduplay.core.export_service import ExportService

        svc = ExportService()
        payload = json.dumps({"project_id": "demo-project"}, ensure_ascii=False)
        payload_b64 = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
        token = Fernet(svc._firebase_service_account_fernet_key()).encrypt(payload_b64.encode("utf-8")).decode("utf-8")

        with patch.dict(
            os.environ,
            {
                "EDUPLAY_FIREBASE_SERVICE_ACCOUNT_B64": "",
                "EDUPLAY_FIREBASE_SERVICE_ACCOUNT_FERNET": token,
            },
            clear=False,
        ):
            self.assertEqual(svc._read_service_account_b64(), payload_b64)
            self.assertEqual(svc._decode_service_account_info(svc._read_service_account_b64()), {"project_id": "demo-project"})


if __name__ == "__main__":
    unittest.main()
