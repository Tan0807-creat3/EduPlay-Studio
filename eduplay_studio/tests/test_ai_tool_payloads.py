import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAiToolPayloads(unittest.TestCase):
    def test_build_updated_question_accepts_flat_payload(self):
        from eduplay.core.ai_tool_payloads import build_updated_question

        payload = {"question_id": "q1", "explanation": "mới"}
        current_q = {"id": "q1", "question": "cũ", "explanation": "cũ"}
        new_q = build_updated_question(payload, current_q)
        self.assertEqual(new_q.get("id"), "q1")
        self.assertEqual(new_q.get("explanation"), "mới")

    def test_build_updated_question_accepts_patch_string(self):
        from eduplay.core.ai_tool_payloads import build_updated_question

        payload = {"question_id": "q1", "patch": '{"explanation":"mới"}'}
        current_q = {"id": "q1", "question": "cũ", "explanation": "cũ"}
        new_q = build_updated_question(payload, current_q)
        self.assertEqual(new_q.get("explanation"), "mới")

    def test_build_updated_question_accepts_patch_plain_string(self):
        from eduplay.core.ai_tool_payloads import build_updated_question

        payload = {"question_id": "q1", "patch": "mới"}
        current_q = {"id": "q1", "question": "cũ", "explanation": "cũ"}
        new_q = build_updated_question(payload, current_q)
        self.assertEqual(new_q.get("explanation"), "mới")

    def test_build_updated_question_prefers_full_question(self):
        from eduplay.core.ai_tool_payloads import build_updated_question

        payload = {"question_id": "q1", "question": {"id": "q1", "question": "mới"}}
        current_q = {"id": "q1", "question": "cũ", "explanation": "cũ"}
        new_q = build_updated_question(payload, current_q)
        self.assertEqual(new_q, {"id": "q1", "question": "mới"})

    def test_build_updated_question_returns_none_on_invalid_payload(self):
        from eduplay.core.ai_tool_payloads import build_updated_question

        payload = {"question_id": "q1"}
        current_q = {"id": "q1", "question": "cũ", "explanation": "cũ"}
        new_q = build_updated_question(payload, current_q)
        self.assertTrue(new_q is None)

    def test_parse_update_question_payload_fallback_kv(self):
        from eduplay.core.ai_tool_payloads import parse_update_question_payload

        raw = 'question_id="q1", explanation="mới"'
        payload = parse_update_question_payload(raw)
        self.assertEqual(payload.get("question_id"), "q1")
        self.assertEqual(payload.get("explanation"), "mới")

    def test_parse_update_question_payload_returns_dict_for_json(self):
        from eduplay.core.ai_tool_payloads import parse_update_question_payload

        raw = '{"question_id":"q1","patch":{"explanation":"mới"}}'
        payload = parse_update_question_payload(raw)
        self.assertEqual(payload.get("question_id"), "q1")
        self.assertEqual((payload.get("patch") or {}).get("explanation"), "mới")

    def test_parse_update_question_payload_accepts_plain_text(self):
        from eduplay.core.ai_tool_payloads import parse_update_question_payload

        raw = "giải thích mới"
        payload = parse_update_question_payload(raw)
        self.assertEqual((payload.get("patch") or {}).get("explanation"), "giải thích mới")

    def test_extract_question_numbers_handles_cau_1_va_5(self):
        from eduplay.core.ai_tool_payloads import extract_question_numbers

        self.assertEqual(extract_question_numbers("sửa câu 1 và 5"), [1, 5])

    def test_extract_question_numbers_handles_q_prefix(self):
        from eduplay.core.ai_tool_payloads import extract_question_numbers

        self.assertEqual(extract_question_numbers("update q3"), [3])


if __name__ == "__main__":
    unittest.main()

