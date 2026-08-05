import os
import re
import sys
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestExportModesAndTiming(unittest.TestCase):
    def test_generate_quiz_game_html_includes_teaching_mode_runtime(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz day hoc",
                "language": "vi",
                "questions": [
                    {
                        "question": "1 + 1 = ?",
                        "type": "multiple_choice",
                        "options": ["1", "2", "3", "4"],
                        "correct_answer": 1,
                        "explanation": "1 + 1 = 2",
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "teaching",
                },
            },
            "classic",
        )

        self.assertIn('"export_mode":"teaching"', html)
        self.assertIn("teachingMode", html)

    def test_generate_quiz_game_html_text_answers_in_teaching_follow_student_flow(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz dien khuyet day hoc",
                "language": "vi",
                "questions": [
                    {
                        "question": "Thu do Viet Nam?",
                        "type": "fill_blank",
                        "correct_answers": ["Ha Noi"],
                        "explanation": "Dap an la Ha Noi",
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "teaching",
                },
            },
            "classic",
        )

        self.assertNotIn("function resolveTeachingTextAnswer(question, isCorrect)", html)
        self.assertNotIn("if (teachingMode && (question.type === 'fill_blank' || question.type === 'short_answer'))", html)
        self.assertIn("if (!isCorrect && showCorrectEnabled && (!teachingMode || textStudentFlow)) {", html)
        self.assertIn("if (question.explanation && showExplanationsEnabled && (!teachingMode || isCorrect || textStudentFlow)) {", html)

    def test_generate_quiz_game_html_normalizes_text_answers_from_single_correct_answer(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz tra loi ngan day hoc",
                "language": "vi",
                "questions": [
                    {
                        "question": "Thu do Viet Nam?",
                        "type": "short_answer",
                        "correct_answer": "Ha Noi",
                        "explanation": "Dap an la Ha Noi",
                    },
                    {
                        "question": "Dien khuyet",
                        "type": "fill_blank",
                        "correct_answers": ["dap an 1", "dap an 2"],
                    },
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "teaching",
                },
            },
            "classic",
        )

        self.assertIn('"type":"short_answer"', html)
        self.assertIn('"type":"fill_blank"', html)
        self.assertIn('"correct_answers":["Ha Noi"]', html)
        self.assertIn('"correct_answers":["dap an 1","dap an 2"]', html)

    def test_generate_quiz_game_html_text_answer_runtime_falls_back_to_single_correct_answer(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz classic text runtime",
                "language": "vi",
                "questions": [
                    {
                        "question": "Thu do Viet Nam?",
                        "type": "short_answer",
                        "correct_answer": "Ha Noi",
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "student",
                },
            },
            "classic",
        )

        self.assertIn(
            "function getRuntimeTextAcceptedAnswers(question){",
            html,
        )
        self.assertIn(
            "const arr = getRuntimeTextAcceptedAnswers(question);",
            html,
        )

    def test_generate_quiz_game_html_fill_blank_renders_inline_input_at_marker(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz dien khuyet inline",
                "language": "vi",
                "questions": [
                    {
                        "question": "Thu do cua Viet Nam la ___",
                        "type": "fill_blank",
                        "answers": ["Ha Noi", "Hà Nội"],
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "student",
                },
            },
            "classic",
        )

        self.assertIn("function renderQuestionPrompt(question, inlineInput = null){", html)
        self.assertIn("displayText.match(/_{3,}/);", html)
        self.assertIn("input.className = 'text-input inline-blank-input';", html)
        self.assertIn("input.placeholder = '';", html)
        self.assertIn(".question-text.fill-blank-inline { display:block; text-align:center; }", html)
        self.assertIn("speakText(getRuntimeQuestionText(question));", html)

    def test_generate_quiz_game_html_embeds_feedback_sound_pools_and_popup_runtime(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz popup am thanh",
                "language": "vi",
                "questions": [
                    {
                        "question": "2 + 2 = ?",
                        "type": "multiple_choice",
                        "options": ["3", "4", "5", "6"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "student",
                },
            },
            "classic",
        )

        self.assertIn('"feedback_sound_pools":{"correct"', html)
        self.assertIn("Well done!", html)
        self.assertIn("Keep learning!", html)
        self.assertIn("function showFeedbackPopup(text, isCorrect, durationMs){", html)
        self.assertIn("function playFeedbackCue(kind, options = {}){", html)
        self.assertIn("const token = showFeedbackPopup(entry.text, isCorrect, durationMs);", html)
        self.assertIn("bindFeedbackPopupToAudio(entry.audio, durationMs, token);", html)
        self.assertIn("font-style:italic;", html)
        self.assertIn("background:transparent;", html)
        self.assertIn("playFeedbackCue('wrong', { useRandomPool: !teachingMode, showPopup: !teachingMode });", html)

    def test_generate_quiz_game_html_keeps_result_mark_out_of_classic_option_layout(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz classic result mark",
                "language": "vi",
                "questions": [
                    {
                        "question": "2 + 2 = ?",
                        "type": "multiple_choice",
                        "options": ["3", "4", "5", "6"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "student",
                },
            },
            "classic",
        )

        self.assertIn(".option-button.btn-classic > .option-inner { position: relative; z-index: 1; }", html)
        self.assertIn(".option-button.btn-classic > .result-mark { position: absolute; z-index: 4; }", html)
        self.assertNotIn(".option-button.btn-classic > * { position: relative; z-index: 1; }", html)

    def test_generate_quiz_game_html_classic_uses_light_theme_for_overlay_cards_and_mobile_buttons(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz classic light theme",
                "language": "vi",
                "questions": [
                    {
                        "question": "2 + 2 = ?",
                        "type": "multiple_choice",
                        "options": ["3", "4", "5", "6"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "student",
                },
            },
            "classic",
        )

        self.assertIn(".loading-card{", html)
        self.assertIn(".intro-card{", html)
        self.assertIn(".popup-panel{background:linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98))", html)
        self.assertIn(".game-over-card {", html)
        self.assertIn("background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98));", html)
        self.assertIn(".time-progress { height: 12px; background: rgba(226, 232, 240, 0.9);", html)
        self.assertIn(".btn-classic { padding: 14px 16px; background: linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 52%, #EFF6FF 100%); color: #111827;", html)
        self.assertIn('<div id="loading-overlay" class="loading-overlay">', html)
        self.assertIn('<div class="intro-card">', html)

    def test_generate_quiz_game_html_classic_has_clearer_click_feedback_states(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz classic click feedback",
                "language": "vi",
                "questions": [
                    {
                        "question": "2 + 2 = ?",
                        "type": "multiple_choice",
                        "options": ["3", "4", "5", "6"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "question_time": 20,
                    "export_mode": "student",
                },
            },
            "classic",
        )

        self.assertIn(".option-button.btn-classic.press-pop {", html)
        self.assertIn("animation: optionPressPop 260ms cubic-bezier(0.22, 1, 0.36, 1);", html)
        self.assertIn(".option-button.btn-classic.selected::before {", html)
        self.assertIn("animation: optionSelectedShine 820ms ease;", html)
        self.assertIn(".option-button.btn-classic.correct {", html)
        self.assertIn("animation: optionCorrectPulse 520ms cubic-bezier(0.22, 1, 0.36, 1);", html)
        self.assertIn(".option-button.btn-classic.incorrect {", html)
        self.assertIn("animation: optionWrongShake 420ms ease;", html)
        self.assertIn("@keyframes optionPressPop {", html)
        self.assertIn("@keyframes optionSelectedShine {", html)
        self.assertIn("function animateOptionPress(btn){", html)
        self.assertIn("animateOptionPress(btn);", html)

    def test_generate_quiz_game_html_matching_lines_use_card_rect_instead_of_zero_sized_anchor(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz classic matching edges",
                "language": "vi",
                "questions": [
                    {
                        "question": "Noi cap",
                        "type": "matching",
                        "pairs": [
                            {"left": "A", "right": "1"},
                            {"left": "B", "right": "2"},
                        ],
                    }
                ],
                "game_config": {"question_time": 20},
            },
            "classic",
        )

        self.assertIn("const rect = el.getBoundingClientRect();", html)
        self.assertIn("const scaleX = w / Math.max(1, wrapRect.width || w);", html)
        self.assertIn("const scaleY = h / Math.max(1, wrapRect.height || h);", html)
        self.assertNotIn(
            "const rect = anchor ? anchor.getBoundingClientRect() : el.getBoundingClientRect();",
            html,
        )

    def test_generate_quiz_game_html_reveal_delay_only_applies_to_millionaire(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_quiz_game_html(
            {
                "id": "p1",
                "name": "Quiz classic no reveal delay",
                "language": "vi",
                "questions": [
                    {
                        "question": "1 + 1 = ?",
                        "type": "multiple_choice",
                        "options": ["1", "2", "3", "4"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {"question_time": 20, "reveal_delay_ms": 2500},
            },
            "classic",
        )

        self.assertIn(
            "const delayMs = millionaireMode ? parseInt(settings.reveal_delay_ms||1500) : 0;",
            html,
        )
        self.assertNotIn(
            "const delayMs = parseInt(settings.reveal_delay_ms||1500);",
            html,
        )

    def test_generate_fishing_game_html_includes_teaching_mode_runtime(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_fishing_game_html(
            {
                "id": "p1",
                "name": "Bat ca day hoc",
                "language": "vi",
                "questions": [
                    {
                        "question": "Noi cap dung",
                        "type": "matching",
                        "pairs": [
                            {"left": "A", "right": "1"},
                            {"left": "B", "right": "2"},
                        ],
                        "explanation": "A-1, B-2",
                    }
                ],
                "game_config": {
                    "question_time": 25,
                    "export_mode": "teaching",
                },
            }
        )

        self.assertIn('"export_mode":"teaching"', html)
        self.assertIn("teachingMode", html)

    def test_generate_fishing_game_html_contains_matching_runtime_and_large_fish(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_fishing_game_html(
            {
                "id": "p1",
                "name": "Bat ca noi cap",
                "language": "vi",
                "questions": [
                    {
                        "question": "Noi cap dung",
                        "type": "matching",
                        "pairs": [
                            {"left": "A", "right": "1"},
                            {"left": "B", "right": "2"},
                        ],
                    }
                ],
                "game_config": {
                    "question_time": 25,
                    "fish_count": 3,
                    "export_mode": "teaching",
                },
            }
        )

        self.assertIn("buildMatchingBoard(pairs);", html)
        self.assertIn("function drawMatchingLinks()", html)
        self.assertIn("let minW = 130, maxW = 175;", html)

    def test_generate_fishing_game_html_normalizes_true_false_labels_and_boolean_answer(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_fishing_game_html(
            {
                "id": "p1",
                "name": "Bat ca dung sai",
                "language": "vi",
                "questions": [
                    {
                        "question": "Tuyen truyen qua mang co phai la mot phan khong?",
                        "type": "true_false",
                        "options": ["Sai", "Đúng"],
                        "correct_answer": True,
                    }
                ],
                "game_config": {
                    "question_time": 25,
                    "fish_count": 1,
                },
            }
        )

        self.assertIn('"type":"true_false"', html)
        self.assertIn('"options":["Đúng","Sai"]', html)
        self.assertIn('"correctAnswer":true', html)
        self.assertIn('"correct_answer":true', html)

    def test_generate_fishing_game_html_declares_matching_state_and_teaching_matching_logic(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_fishing_game_html(
            {
                "id": "p1",
                "name": "Bat ca noi cap mep the",
                "language": "vi",
                "questions": [
                    {
                        "question": "Noi cap dung",
                        "type": "matching",
                        "pairs": [
                            {"left": "A", "right": "1"},
                            {"left": "B", "right": "2"},
                        ],
                    }
                ],
                "game_config": {
                    "question_time": 25,
                    "fish_count": 2,
                },
            }
        )

        self.assertIn("let matchingState = null;", html)
        self.assertIn("function initMatchingState(pairs) {", html)
        self.assertIn("if (teachingMode && leftIndex !== rightIndex) {", html)
        self.assertIn("flashWrongMatchCard(matchingState.leftButtons[leftIndex]);", html)
        self.assertIn("if (teachingMode && allMatchingPairsConnected()) {", html)
        self.assertIn("setTimeout(() => { applyResult(true); }, 180);", html)

    def test_fishing_template_declares_matching_state_and_teaching_matching_logic(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("let matchingState = null;", html)
        self.assertIn("function buildMatchingBoard(pairs) {", html)
        self.assertIn("function drawMatchingLinks() {", html)
        self.assertIn("if (teachingMode && leftIndex !== rightIndex) {", html)
        self.assertIn("flashWrongMatchCard(matchingState.rightButtons[rightIndex]);", html)
        self.assertIn("setTimeout(() => { applyResult(true); }, 180);", html)

    def test_fishing_template_text_answers_normalize_single_or_array_correct_answer(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn(
            "function getTextQuestionAcceptedAnswers(question) {",
            html,
        )
        self.assertIn(
            "pushValues(question && question.correct_answers);",
            html,
        )
        self.assertIn(
            "pushValues(question && question.answers);",
            html,
        )
        self.assertIn(
            "pushValues(question && question.answer_list);",
            html,
        )
        self.assertIn(
            "const acceptedAnswers = getTextQuestionAcceptedAnswers(q);",
            html,
        )
        self.assertIn(
            "const ok = acceptedAnswers.map(normalizeText).includes(val);",
            html,
        )

    def test_fishing_template_normalizes_fill_blank_type_prompt_and_answers_before_render(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("function normalizeFishingQuestionType(question) {", html)
        self.assertIn("function getFishingQuestionText(question) {", html)
        self.assertIn("function collectFishingTextAnswers(question) {", html)
        self.assertIn("const normalizedType = normalizeFishingQuestionType(src);", html)
        self.assertIn("currentQuestionType = normalizeFishingQuestionType(question);", html)
        self.assertIn("question: getFishingQuestionText(src),", html)

    def test_fishing_template_renders_correct_answer_feedback_for_wrong_or_timeout(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("function renderQuestionFeedback(question, includeCorrectAnswer) {", html)
        self.assertIn("answerHead.textContent = '{{ i18n_correct_answer }}';", html)
        self.assertIn(
            "return getQuestionPairs(question).map(pair => `${pair.left} -> ${pair.right}`).filter(Boolean);",
            html,
        )
        self.assertIn("return getTextQuestionAcceptedAnswers(question);", html)
        self.assertIn("if (renderQuestionFeedback(question, true) || shouldPauseForContinue) {", html)
        self.assertIn("if (renderQuestionFeedback(question, true)) {", html)

    def test_fishing_template_uses_light_hud_styles_and_tighter_score_digits(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.96));", html)
        self.assertIn("box-shadow: 0 12px 26px rgba(186, 230, 253, 0.4);", html)
        self.assertIn("container.style.gap = '0';", html)
        self.assertIn("const overlapPx = Math.max(6, Math.round(h * 0.18));", html)
        self.assertIn("img.style.marginRight = (i < s.length - 1) ? `${-overlapPx}px` : '0';", html)
        self.assertIn("span.style.marginRight = (i < s.length - 1) ? '-0.08em' : '0';", html)
        self.assertIn('<span class="score-label">{{ i18n_score }}:</span><span id="final-score">0</span>', html)
        self.assertIn(".game-over-card .score-label {", html)

    def test_fishing_template_choice_and_motion_runtime_include_teaching_mode_and_smoother_fish(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("function handleChoiceAttempt(selectedIndex) {", html)
        self.assertIn("config.exportMode = String(cfg.export_mode || 'student').toLowerCase() === 'teaching' ? 'teaching' : 'student';", html)
        self.assertIn("teachingMode = config.exportMode === 'teaching';", html)
        self.assertIn("selectedEl.classList.add('wrong');", html)
        self.assertIn("optionEls[lastSelectedIndex].classList.add(isCorrect ? 'correct' : 'wrong');", html)
        self.assertIn("turnCooldown: 1.6 + Math.random() * 1.2", html)
        self.assertNotIn("Math.random() < 0.003", html)

    def test_fishing_template_submit_flow_stops_timer_and_swaps_to_continue(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("function stopQuestionCountdown() {", html)
        self.assertIn("function showContinueOnly() {", html)
        self.assertIn("stopQuestionCountdown();", html)
        self.assertIn("submitBtn.style.display = 'inline-block';", html)
        self.assertIn("submitBtn.textContent = continueBtn ? continueBtn.textContent : '{{ i18n_next }}';", html)
        self.assertIn("continueBtn.style.display = 'none';", html)

    def test_fishing_template_text_input_is_centered_and_box_sized(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn(".text-answer-layout {", html)
        self.assertIn(".text-answer-wrap {", html)
        self.assertIn("width: min(92%, 560px);", html)
        self.assertIn("margin: 0 auto;", html)
        self.assertIn("box-sizing: border-box;", html)
        self.assertIn("optionsContainer.className = 'options-stack text-answer-layout';", html)
        self.assertIn("inputWrap.className = 'text-answer-wrap';", html)

    def test_fishing_template_teaching_mode_keeps_fish_alive_on_wrong_non_text_answers(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("function resolveTrueFalseMeta(question) {", html)
        self.assertIn("const tfOptions = resolveTrueFalseMeta(question).options;", html)
        self.assertIn("return resolveTrueFalseMeta(question).correct ? 0 : 1;", html)
        self.assertIn("applyResult(val === resolveTrueFalseMeta(question).correct);", html)
        self.assertIn("function shouldKeepFishOnWrongAnswer() {", html)
        self.assertIn("return teachingMode && currentQuestionType !== 'fill_blank' && currentQuestionType !== 'short_answer';", html)
        self.assertIn("function turnCurrentFishIntoSkeleton() {", html)
        self.assertIn("turnCurrentFishIntoSkeleton();", html)

    def test_fishing_template_does_not_apply_reveal_delay_setting(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "templates_fish"
            / "fishing_game.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertNotIn("reveal_delay_ms", html)
        self.assertNotIn("const delayMs =", html)

    def test_generate_millionaire_html_preserves_per_question_time_limits(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_millionaire_html(
            {
                "id": "p1",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Q1",
                        "options": ["A1", "B1", "C1", "D1"],
                        "correct_answer": 1,
                        "time_limit": 45,
                    },
                    {
                        "question": "Q2",
                        "options": ["A2", "B2", "C2", "D2"],
                        "correct_answer": 2,
                        "time_limit": 20,
                    },
                ],
                "game_config": {
                    "game_type": "Ai là triệu phú",
                    "question_time": 30,
                    "export_mode": "teaching",
                },
            }
        )

        self.assertRegex(html, r'"time_limit"\s*:\s*45')
        self.assertRegex(html, r'"time_limit"\s*:\s*20')
        self.assertNotIn("default_time === 45", html)
        self.assertNotIn("window.EDU_QUESTIONS[i].time_limit = tl;", html)

    def test_generate_millionaire_html_exposes_runtime_export_mode(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_millionaire_html(
            {
                "id": "p1",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Q1",
                        "options": ["A1", "B1", "C1", "D1"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "game_type": "Ai là triệu phú",
                    "question_time": 30,
                    "export_mode": "teaching",
                },
            }
        )

        self.assertIn("window.EDU_MILLIONAIRE_MODE", html)
        self.assertIn("maybeResolveTeachingMillionaire(ans, questionObj)", html)
        self.assertIn("window.__EP_WRONG && !isMillionaireTeachingMode()", html)

    def test_generate_millionaire_html_keeps_default_correct_audio_for_teaching_mode(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_millionaire_html(
            {
                "id": "p1",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Q1",
                        "options": ["A1", "B1", "C1", "D1"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "game_type": "Ai là triệu phú",
                    "question_time": 30,
                    "export_mode": "teaching",
                },
            }
        )

        self.assertNotIn('"feedback_sound_pools":{"correct"', html)
        self.assertIn('case "correctAnswer":', html)
        self.assertNotIn('window.__EP_MILLIONAIRE_TEACHING && playMillionaireFeedbackPool("correct")', html)

    def test_generate_millionaire_html_uses_previous_level_for_wrong_answer(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        html = svc._generate_millionaire_html(
            {
                "id": "p1",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Q1",
                        "options": ["A1", "B1", "C1", "D1"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {"game_type": "Ai là triệu phú"},
            }
        )

        self.assertNotIn("window.__EP_GAMEOVER_LEVEL = actualLevel;", html)

    def test_millionaire_assets_teaching_mode_keeps_wrong_choice_red_until_correct(self):
        base = Path(__file__).resolve().parents[1] / "assets_bundle" / "millionaire" / "js"
        functions_js = (base / "functions.js").read_text(encoding="utf-8")
        app_js = (base / "app.js").read_text(encoding="utf-8")

        expected_branch = re.compile(
            r"if \(isMillionaireTeachingMode\(\)\) \{[\s\S]*?"
            r"maybeResolveTeachingMillionaire\(ans, questionObj\)[\s\S]*?"
            r"return;\s*\}",
            re.MULTILINE,
        )

        self.assertRegex(functions_js, expected_branch)
        self.assertRegex(app_js, expected_branch)

    def test_millionaire_assets_show_explanation_after_correct_highlight(self):
        base = Path(__file__).resolve().parents[1] / "assets_bundle" / "millionaire" / "js"
        functions_js = (base / "functions.js").read_text(encoding="utf-8")
        app_js = (base / "app.js").read_text(encoding="utf-8")

        correct_branch = re.compile(
            r"function highLightAnswerGreen\(id, correctAnswer, questionObj\) \{[\s\S]*?"
            r"addClass\('answerCorrect'\)[\s\S]*?"
            r"setTimeout\(function\s*\(\)\s*\{[\s\S]*?"
            r"showExplanation\(correctAnswer, questionObj\);[\s\S]*?\}\s*,\s*650\s*\);[\s\S]*?\}",
            re.MULTILINE,
        )
        wrong_branch = re.compile(
            r"function highLightAnswerRed\(id, ans, questionObj\) \{[\s\S]*?"
            r"highlightCorrectAnswer\(ans\);[\s\S]*?"
            r"setTimeout\(function\s*\(\)\s*\{[\s\S]*?"
            r"showExplanation\(ans, questionObj\);[\s\S]*?\}\s*,\s*650\s*\);[\s\S]*?\}",
            re.MULTILINE,
        )

        self.assertRegex(functions_js, correct_branch)
        self.assertRegex(app_js, correct_branch)
        self.assertRegex(functions_js, wrong_branch)
        self.assertRegex(app_js, wrong_branch)

    def test_millionaire_assets_delay_next_timer_until_score_cutscene_finishes(self):
        app_js = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "millionaire"
            / "js"
            / "app.js"
        ).read_text(encoding="utf-8")

        self.assertIn("function getMillionaireCutsceneDelay()", app_js)
        self.assertIn("window.__EP_SCORE_CUTSCENE_UNTIL = Date.now() + 7500;", app_js)
        self.assertIn("var resumeDelay = getMillionaireCutsceneDelay();", app_js)
        self.assertIn("window.__EP_TIMER_RESUME_TIMEOUT = setTimeout(function() {", app_js)
        self.assertIn("timerID.TimeCircles().stop();", app_js)

    def test_millionaire_assets_freeze_timer_while_answer_result_is_pending(self):
        base = Path(__file__).resolve().parents[1] / "assets_bundle" / "millionaire" / "js"
        functions_js = (base / "functions.js").read_text(encoding="utf-8")
        app_js = (base / "app.js").read_text(encoding="utf-8")

        self.assertIn("window.__EP_ANSWER_PENDING", functions_js)
        self.assertIn("if (window.__EP_ANSWER_PENDING) {", functions_js)
        self.assertIn("window.__EP_ANSWER_PENDING = false;", functions_js)
        self.assertIn("window.__EP_ANSWER_PENDING = true;", app_js)
        self.assertIn("window.__EP_ANSWER_PENDING = false;", app_js)
        self.assertIn("try { window.__EP_ANSWER_PENDING = true; } catch(e) {}", app_js)
        self.assertIn("try { window.__EP_ANSWER_PENDING = false; } catch(e) {}", functions_js)


if __name__ == "__main__":
    unittest.main()
