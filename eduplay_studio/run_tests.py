import sys
import io
import unittest

sys.path.insert(0, ".")

loader = unittest.TestLoader()
suite = unittest.TestSuite()
for name in [
    "tests.test_i18n_key_coverage",
    "tests.test_command_palette",
    "tests.test_home_nav_and_browser_filters_ui",
    "tests.test_icon_button_labels_and_editor_header",
    "tests.test_editor_question_actions",
    "tests.test_editor_right_panel_preview",
]:
    suite.addTests(loader.loadTestsFromName(name))

stream = io.StringIO()
runner = unittest.TextTestRunner(stream=stream, verbosity=2)
result = runner.run(suite)

output = stream.getvalue()
for line in output.splitlines():
    if "FAIL:" in line or "ERROR:" in line:
        print(line[:120])
    if "Ran " in line or "OK" in line or "FAILED" in line:
        print(line)
