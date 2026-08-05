
//GET RANDOM NUMBER BETWEEN 2 VALUES
function getRndInteger(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function checkCutScene(x) {
    switch (x) {
        case 1:
        case 2:
        case 3:
        case 4:
            playMusic(x - 1);
            break;
        case 5:
            showScoreCutScene(x - 1);
            break;
        case 6:
        case 7:
        case 8:
        case 9:
            playMusic(x - 1);
            break;
        case 10:
            showScoreCutScene(x - 1);
            break;
        case 11:
        case 12:
        case 13:
        case 14:
        case 15:
            playMusic(x - 1);
            break;
        case 16:
            showGameOverCutScene(x - 1);
            break;
    }
}


// SET HEIGHTS OF AUDIENCE METERS
function setAudienceMeters(a, b, c, d) {

    $("#meter1").animate({
        width: a + "%"
    }, 1500);
    $("#meter2").animate({
        width: b + "%"
    }, 1500);
    $("#meter3").animate({
        width: c + "%"
    }, 1500);
    $("#meter4").animate({
        width: d + "%"
    }, 1500);


}

function disableClick() {
    $('#ans1B').off('click');
    $('#ans2B').off('click');
    $('#ans3B').off('click');
    $('#ans4B').off('click');
    try { $('#ans1B').addClass('locked'); $('#ans2B').addClass('locked'); $('#ans3B').addClass('locked'); $('#ans4B').addClass('locked'); } catch(e){}
}

function isMillionaireTeachingMode() {
    try {
        var mode = window.EDU_MILLIONAIRE_MODE || window.__EP_MILLIONAIRE_MODE || (((window.EDU_PROJECT || {}).game_config || {}).export_mode) || 'student';
        return String(mode || 'student').toLowerCase() === 'teaching';
    } catch(e) {
        return false;
    }
}

function getAnswerBlocks() {
    return ['ans1B', 'ans2B', 'ans3B', 'ans4B']
        .map(function(id) { return document.getElementById(id); })
        .filter(Boolean);
}

function getAnswerTextFromBlock(el) {
    try {
        var span = el ? el.querySelector('span') : null;
        return String((span && span.textContent) || '').trim();
    } catch(e) {
        return '';
    }
}

function maybeResolveTeachingMillionaire(correctAnswer, questionObj) {
    try {
        if (!isMillionaireTeachingMode()) return false;
        var remaining = getAnswerBlocks().filter(function(el) {
            return !el.classList.contains('locked') && !el.classList.contains('answerIncorrect') && el.offsetParent !== null;
        });
        if (remaining.length !== 1) return false;
        var winner = remaining[0];
        if (getAnswerTextFromBlock(winner) !== String(correctAnswer || '').trim()) return false;
        disableClick();
        try { window.__EP_WRONG = false; } catch(e) {}
        highLightAnswerGreen(winner, correctAnswer, questionObj);
        return true;
    } catch(e) {
        return false;
    }
}

function markMillionaireAnswerPending() {
    try {
        var api = $('#timer').TimeCircles();
        if (api && api.getTime) {
            window.__EP_PENDING_REMAINING_TIME = Math.max(0, Math.ceil(api.getTime()));
        }
    } catch(e) {}
    try { window.__EP_ANSWER_PENDING = true; } catch(e) {}
}

function clearMillionaireAnswerPending() {
    try { window.__EP_ANSWER_PENDING = false; } catch(e) {}
    try { window.__EP_PENDING_REMAINING_TIME = null; } catch(e) {}
}

function resumeMillionaireTimerAfterWrong() {
    try {
        var remaining = parseInt(window.__EP_PENDING_REMAINING_TIME || 0, 10);
        if (!(remaining > 0)) {
            clearMillionaireAnswerPending();
            return;
        }
        var timer = $('#timer');
        try {
            var tel = document.getElementById('timer');
            if (tel) tel.setAttribute('data-timer', String(remaining));
        } catch(e) {}
        try { timer.data('timer', String(remaining)); } catch(e) {}
        try {
            var api = timer.TimeCircles();
            if (api && api.stop) api.stop();
            if (api && api.restart) api.restart();
        } catch(e) {}
    } catch(e) {}
    clearMillionaireAnswerPending();
}

function stopMillionaireTickingEffects() {
    try { stopEffect("ticktock"); } catch(e) {}
    try { window.__ticktockPlaying = false; } catch(e) {}
}

function getMillionaireTimerLockRemaining() {
    try {
        var lockUntil = parseInt(window.__EP_TIMER_LOCK_UNTIL || 0, 10);
        return Math.max(0, lockUntil - Date.now());
    } catch(e) {
        return 0;
    }
}

function lockMillionaireTimer(ms) {
    try {
        var duration = Math.max(0, parseInt(ms || 0, 10));
        var nextLockUntil = Date.now() + duration;
        var currentLockUntil = parseInt(window.__EP_TIMER_LOCK_UNTIL || 0, 10);
        window.__EP_TIMER_LOCK_UNTIL = Math.max(currentLockUntil, nextLockUntil);
    } catch(e) {
        window.__EP_TIMER_LOCK_UNTIL = Date.now();
    }
    try { $('#timer').TimeCircles().stop(); } catch(e) {}
    stopMillionaireTickingEffects();
}

function clearMillionaireTimerLock() {
    try { window.__EP_TIMER_LOCK_UNTIL = 0; } catch(e) {}
}

function shouldKeepMillionaireTimerStopped() {
    try {
        if (window.__EP_ANSWER_PENDING) return true;
        var explanationBlock = document.getElementById('explanationBlock');
        if (explanationBlock && explanationBlock.style.display !== 'none' && explanationBlock.style.visibility !== 'hidden' && explanationBlock.offsetParent !== null) {
            return true;
        }
        var endScene = document.getElementById('endGameCutScene');
        if (endScene && endScene.style.display !== 'none' && endScene.offsetParent !== null) {
            return true;
        }
    } catch(e) {}
    return false;
}

function setMillionaireAnswerInteractivity(locked) {
    ['ans1B', 'ans2B', 'ans3B', 'ans4B'].forEach(function(id) {
        try {
            var el = document.getElementById(id);
            if (!el) return;
            el.style.pointerEvents = locked ? 'none' : '';
            if (locked) {
                el.classList.add('question-transition-lock');
            } else {
                el.classList.remove('question-transition-lock');
            }
        } catch(e) {}
    });
}

function playMillionaireQuestionEntrance() {
    var targets = [
        { id: 'questionBox', delay: 0 },
        { id: 'ans1B', delay: 120 },
        { id: 'ans2B', delay: 190 },
        { id: 'ans3B', delay: 260 },
        { id: 'ans4B', delay: 330 }
    ];
    targets.forEach(function(target) {
        try {
            var el = document.getElementById(target.id);
            if (!el) return;
            el.classList.remove('millionaire-question-intro');
            void el.offsetWidth;
            el.style.setProperty('--question-intro-delay', String(target.delay) + 'ms');
            el.classList.add('millionaire-question-intro');
        } catch(e) {}
    });
    try {
        if (window.__EP_QUESTION_INTRO_TIMEOUT) {
            clearTimeout(window.__EP_QUESTION_INTRO_TIMEOUT);
        }
        window.__EP_QUESTION_INTRO_TIMEOUT = setTimeout(function() {
            targets.forEach(function(target) {
                try {
                    var el = document.getElementById(target.id);
                    if (!el) return;
                    el.classList.remove('millionaire-question-intro');
                    el.style.removeProperty('--question-intro-delay');
                } catch(e) {}
            });
        }, 1000);
    } catch(e) {}
}

function escapeSvgText(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function renderMillionaireArcHeader(message) {
    try {
        var header = document.getElementById('endGameHeader');
        if (!header) return;
        var label = String(message || '').trim();
        var safeLabel = escapeSvgText(label);
        var charCount = label.replace(/\s+/g, '').length;
        var fontSize = 92;
        if (charCount > 24) {
            fontSize = 56;
        } else if (charCount > 18) {
            fontSize = 68;
        } else if (charCount > 12) {
            fontSize = 80;
        }
        header.classList.add('endGameHeaderArc');
        header.style.setProperty('--endgame-arc-font-size', fontSize + 'px');
        header.setAttribute('aria-label', label);
        header.innerHTML =
            '<svg class="endGameArcSvg" viewBox="0 0 1000 360" role="img" aria-hidden="true">' +
                '<defs>' +
                    '<path id="endGameArcPath" d="M 110 250 Q 500 28 890 250"></path>' +
                '</defs>' +
                '<text class="endGameArcText" text-anchor="middle">' +
                    '<textPath href="#endGameArcPath" xlink:href="#endGameArcPath" startOffset="50%">' + safeLabel + '</textPath>' +
                '</text>' +
            '</svg>';
    } catch(e) {}
}

//Reset background colours on answer buttons.
function highlightAnswerReset() {
    $('#ans1B').removeClass('answerCorrect answerIncorrect answerCheck locked').addClass('answer').show();
    $('#ans2B').removeClass('answerCorrect answerIncorrect answerCheck locked').addClass('answer').show();
    $('#ans3B').removeClass('answerCorrect answerIncorrect answerCheck locked').addClass('answer').show();
    $('#ans4B').removeClass('answerCorrect answerIncorrect answerCheck locked').addClass('answer').show();
    try { ['ans1B', 'ans2B', 'ans3B', 'ans4B'].forEach(function(id){ var el=document.getElementById(id); if(el){ el.style.pointerEvents=''; } }); } catch(e){}
    $('#AsktheAudience').fadeOut();
}

//Increase currentLevel and refresh money counter.
function levelUp() {
    setTimeout($.proxy(function () {
        currentLevel += 1;
        actualLevel += 1;
        setLevel(actualLevel);
    }, this), 5000);
}

// END GAME FUNCTION
function gameOver(lvl) {
    setTimeout($.proxy(function () {

        showGameOverCutScene(lvl);
        console.log("Game Over");

    }, this), 4000);

    return false;
}

//HIGHLIGHT SELECTED ANSWER ORANGE.
function highLightAnswer(id) {
    stopMusic(actualLevel - 1);
    playEffect("finalAnswer");
    try { $('#timer').TimeCircles().stop(); } catch(e){}
    $('#' + id).hide().removeClass('answer').addClass('answerCheck').fadeIn(1000);
}
//IF ANSWER CORRECT, HIGHLIGHT ANSWER AS GREEN (CORRECT)
function highLightAnswerGreen(id, correctAnswer, questionObj) {
    setTimeout($.proxy(function () {
        stopEffect(currentEffect);
        playEffect("correctAnswer");
        try { $('#timer').TimeCircles().stop(); } catch(e){}
        try { window.__EP_ANSWER_PENDING = false; } catch(e) {}
        $(id).removeClass('answerCheck').addClass('answerCorrect').fadeIn(200).fadeOut(200).fadeIn(200).fadeOut(200).fadeIn(200);
        setTimeout(function() {
            showExplanation(correctAnswer, questionObj);
            $('body').focus();
        }, 650);
    }, this), 1000); // Delay for visual effects
}

//HIGHLIGHT INCORRECT ANSWER
function highLightAnswerRed(id, ans, questionObj) {
    if (isMillionaireTeachingMode()) {
        setTimeout($.proxy(function () {
            playEffect("wrongAnswer");
            stopEffect("finalAnswer");
            try { $('#timer').TimeCircles().stop(); } catch(e){}
            try {
                var el = (id && id.nodeType === 1) ? id : document.getElementById(String(id || '').replace(/^#/, ''));
                if (el) {
                    $(el).removeClass('answerCheck').addClass('answerIncorrect locked').fadeIn(200).fadeOut(200).fadeIn(200);
                    el.style.pointerEvents = 'none';
                }
            } catch(e) {}
            if (maybeResolveTeachingMillionaire(ans, questionObj)) {
                return;
            }
            resumeMillionaireTimerAfterWrong();
        }, this), 1000);
        return;
    }
    setTimeout($.proxy(function () {
        playEffect("wrongAnswer");
        stopEffect("finalAnswer");
        try { $('#timer').TimeCircles().stop(); } catch(e){}
        try { window.__EP_ANSWER_PENDING = false; } catch(e) {}
        $(id).removeClass('answerCheck').addClass('answerIncorrect').fadeIn(200).fadeOut(200).fadeIn(200).fadeOut(200).fadeIn(200);

        highlightCorrectAnswer(ans);
        setTimeout(function() {
            showExplanation(ans, questionObj);
            $('body').focus();
        }, 650);
    }, this), 1000); // Delay for visual effects
}

//SEARCH FOR CORRECT ANSWER AND HIGHLIGHT
function highlightCorrectAnswer(ans) {
    try {
        var target = String(ans||'');
        var map = [
            {block:'#ans1B', text:'#ans1'},
            {block:'#ans2B', text:'#ans2'},
            {block:'#ans3B', text:'#ans3'},
            {block:'#ans4B', text:'#ans4'}
        ];
        map.forEach(function(p){
            try{
                var t = document.querySelector(p.text);
                var b = document.querySelector(p.block);
                if (t && b) {
                    var txt = String((t.textContent||'')).trim();
                    if (txt === target) {
                        $('#'+b.id).removeClass('answerCheck').addClass('answerCorrect');
                    }
                }
            }catch(_){}
        });
    } catch(_) {}
    $('#ans1B').prop('disabled', true);
    $('#ans2B').prop('disabled', true);
    $('#ans3B').prop('disabled', true);
    $('#ans4B').prop('disabled', true);


}

function setMoney(lvl) {
    var newScore = 0;

    switch (lvl) {
        case 0:
            newScore = 0;
            break;
        case 1:
            newScore = 100;
            break;
        case 2:
            newScore = 250;
            break;
        case 3:
            newScore = 500;
            break;
        case 4:
            newScore = 1000;
            break;
        case 5:
            newScore = 2000;
            break;
        case 6:
            newScore = 4000;
            break;
        case 7:
            newScore = 8000;
            break;
        case 8:
            newScore = 16000;
            break;
        case 9:
            newScore = 32000;
            break;
        case 10:
            newScore = 64000;
            break;
        case 11:
            newScore = 125000;
            break;
        case 12:
            newScore = 250000;
            break;
        case 13:
            newScore = 500000;
            break;
        case 14:
            newScore = 1000000;
            break;
        case 15:
            newScore = 1000000;
            break;

        default:
            newScore = 0;
    }
    return newScore;

}

//SET LEVEL - Updates current level and points. (lvl = 1 to 15)
function setLevel(lvl) {
    var setLevel = lvl; // SET FUNCTION INPUT
    var levelID = $('#q' + lvl); // GET LEVEL ELEMENT ID
    var percent = levelID.data("id");


    levelDOM.html(currentLevel); // UPDATE LEVEL # ON DOM
    actualDOM.html("Question " + actualLevel);
    //ANIMATE PROGRESS BAR FILL
    try {
        var fill = 0;
        try {
            var el = document.getElementById('q' + lvl);
            var raw = el ? (el.getAttribute('data-id') || '') : '';
            var p = parseFloat(String(raw).replace('%', ''));
            if (!isNaN(p)) {
                p = Math.max(0, Math.min(100, p));
                fill = Math.max(0, Math.min(100, 100 - p));
            } else {
                fill = Math.max(0, Math.min(100, (parseFloat(lvl) || 0) * (100 / 15)));
            }
        } catch (e1) {
            fill = Math.max(0, Math.min(100, (parseFloat(lvl) || 0) * (100 / 15)));
        }
        try {
            var pb = document.querySelector('.progressBar');
            var pl = document.querySelector('.progressLevel');
            if (pb) {
                pb.style.background = '#020617';
                pb.style.border = '1px solid rgba(227,171,40,0.75)';
                pb.style.borderRadius = '10px';
                pb.style.overflow = 'hidden';
            }
            if (pl) {
                pl.style.background = '#E3AB28';
                pl.style.minHeight = '24px';
                pl.style.borderRadius = '9px';
            }
        } catch (e2) {}
        try {
            var plWrap = $('.progressLevel');
            if (plWrap && plWrap.stop && plWrap.animate) {
                plWrap.stop(true).animate({ height: fill + '%' }, 500);
            } else {
                var plEl = document.querySelector('.progressLevel');
                if (plEl) plEl.style.height = fill + '%';
            }
        } catch (e3) {
            var plEl2 = document.querySelector('.progressLevel');
            if (plEl2) plEl2.style.height = fill + '%';
        }
    } catch (e) {
        try {
            var plEl3 = document.querySelector('.progressLevel');
            if (plEl3) {
                plEl3.style.minHeight = '24px';
                plEl3.style.height = '0%';
            }
        } catch (e4) {}
    }

    //SET HIGHLIGHT ON LEVEL
    levelID.addClass("outer checkPointHL");
    levelDOM.html(currentLevel);
    var score = setMoney(currentLevel - 1);

    var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',')
    $('#scoreValue').animateNumber({
        number: score,
        numberStep: comma_separator_number_step
    });
    $("#scoreValue").fadeIn(200).fadeOut(200).fadeIn(200).fadeOut(200).fadeIn(200);

}

// showScoreCutScene(10);

function showScoreCutScene(lvl) {
    try { $('#timer').TimeCircles().stop(); } catch(e){}
    lockMillionaireTimer(7500);
    try { window.__EP_SCORE_CUTSCENE_UNTIL = Date.now() + 7500; } catch(e){}
    $('#scoreCutScene').fadeIn(1000);

    playEffect("beginGame1");

    var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',')
    $('#sceneScoreValue').animateNumber({
        number: setMoney(lvl),
        numberStep: comma_separator_number_step
    }, 5000);

    setTimeout($.proxy(function () {
        $('#displayScore').fadeIn(200).fadeOut(200).fadeIn(200).fadeOut(200).fadeIn(200);
    }, this), 5000);

    setTimeout($.proxy(function () {
        $('#scoreCutScene').fadeOut(1000);
    }, this), 6500);

    setTimeout($.proxy(function () {
        playMusic(actualLevel - 1);
        try { window.__EP_SCORE_CUTSCENE_UNTIL = 0; } catch(e){}
        clearMillionaireTimerLock();
    }, this), 7500);
}

function toggleShowHide(target) {
    var el = null;
    if (window.jQuery && target instanceof jQuery) {
        el = target[0];
    } else if (typeof target === 'string') {
        el = document.querySelector(target);
    } else if (target && target.nodeType === 1) {
        el = target;
    } else {
        return;
    }
    var className = (el.getAttribute && el.getAttribute('class')) || '';
    if (className.indexOf("show") !== -1) {
        el.classList.remove("show");
        el.classList.add("hide");
    } else {
        el.classList.remove("hide");
        el.classList.add("show");
    }
}

function initTimer() {
    if (window.__EP_TIMER_LISTENER_BOUND) {
        return;
    }
    window.__EP_TIMER_LISTENER_BOUND = true;
    var timer = $('#timer');
    timer.TimeCircles().addListener(function () {
        if (getMillionaireTimerLockRemaining() > 0) {
            try { timer.TimeCircles().stop(); } catch(e) {}
            stopMillionaireTickingEffects();
            return;
        }
        clearMillionaireTimerLock();
        if (shouldKeepMillionaireTimerStopped()) {
            try { timer.TimeCircles().stop(); } catch(e) {}
            stopMillionaireTickingEffects();
            return;
        }
        if (window.__EP_ANSWER_PENDING) {
            try { timer.TimeCircles().stop(); } catch(e) {}
            stopMillionaireTickingEffects();
            return;
        }
        var time = timer.TimeCircles().getTime()
        if (time < 1) {
            timer.TimeCircles().stop();
            timer.data('timer', 0);
            try { window.__EP_ANSWER_PENDING = false; } catch(e) {}
            stopMusic(actualLevel - 1);
            try{ stopEffect("ticktock"); window.__ticktockPlaying = false; }catch(e){}
            if (isMillionaireTeachingMode()) {
                try {
                    var qObj = (typeof questions !== 'undefined' && Array.isArray(questions)) ? questions[currentLevel - 1] : null;
                    var correctAnswer = qObj ? qObj.correct_answer : '';
                    highlightCorrectAnswer(correctAnswer);
                    disableClick();
                    try { window.__EP_WRONG = false; } catch(ex) {}
                    showExplanation(correctAnswer, qObj || {});
                } catch(ex) {
                    playEffect("wrongAnswer");
                    showExplanation('', {});
                }
                console.log("Out of Time - Reveal Answer");
                return;
            }
            playEffect("wrongAnswer");
            try { window.__EP_WRONG = true; window.__EP_GAMEOVER_LEVEL = actualLevel - 1; } catch(ex) {}
            showGameOverCutScene(actualLevel - 1);
            console.log("Out of Time - Game Over!");
        }

        if (time > 0 && time < 7.995) {
            if (!window.__ticktockPlaying) {
                playEffect("ticktock");
                window.__ticktockPlaying = true;
            }
        }
    });
}

function showGameOverCutScene(lvl) {
    $('#endGameCutScene').fadeIn(fadeTime);
    try {
        if (window.__EP_TIMER_RESUME_TIMEOUT) {
            clearTimeout(window.__EP_TIMER_RESUME_TIMEOUT);
            window.__EP_TIMER_RESUME_TIMEOUT = null;
        }
    } catch(e) {}
    clearMillionaireTimerLock();
    try{ stopEffect("ticktock"); window.__ticktockPlaying = false; }catch(e){}
    $('#timer').TimeCircles().stop();
    var resolvedLevel = Math.max(0, parseInt(lvl || 0, 10));
    var isWinner = resolvedLevel >= 15;
    var winMessages = [
        "You are a millionaire!",
        "Welcome to the new millionaire!"
    ];
    var loseMessages = [
        "Nice try!",
        "Better luck next time!",
        "Come back stronger!"
    ];
    function pickRandomMessage(messages) {
        return messages[Math.floor(Math.random() * messages.length)];
    }
    if (isWinner) {
        stopMusic(actualLevel - 1);
        playEffect("winner");
        finalScore = setMoney(15);
    } else {
        finalScore = setMoney(resolvedLevel);
    }
    renderMillionaireArcHeader(pickRandomMessage(isWinner ? winMessages : loseMessages));
    $('#endGameScore').text('0');
    $('#exitGameBtn').hide().fadeIn(200);

    var comma_separator_number_step = $.animateNumber.numberStepFactories.separator(',');
    $('#endGameScore').animateNumber({
        number: finalScore,
        numberStep: comma_separator_number_step
    }, 1000);

    setTimeout($.proxy(function () {
        $('#endGameScoreHeader').fadeIn(200).fadeOut(200).fadeIn(200).fadeOut(200).fadeIn(200);
    }, this), 1200);

}




//SHUFFLES AN ARRAY - TO REORDER INCORRECT QUESTIONS
function shuffle(array) {
    var m = array.length,
        t, i;

    // While there remain elements to shuffle…
    while (m) {

        // Pick a remaining element…
        i = Math.floor(Math.random() * m--);

        // And swap it with the current element.
        t = array[m];
        array[m] = array[i];
        array[i] = t;
    }

    return array;
}

//load question from questions array and shuffle answers.
function loadQuestion(qObj) {


    highlightAnswerReset();
    console.log("Correct Answer - " + qObj.correct_answer);
    var qText = $('#question');
    var a1Text = $('#ans1');
    var a2Text = $('#ans2');
    var a3Text = $('#ans3');
    var a4Text = $('#ans4');

    var q = qObj.question; // set question
    try {
        var lvl = (typeof actualLevel === 'number' ? actualLevel : (typeof currentLevel === 'number' ? currentLevel : 1));
        var hasPrefix = /^(?:(?:câu|cau|question|q|pregunta|frage)\s*(?:hỏi|hoi|so)?(?:\s+số)?\s*\d+)\s*[:.\-]?\s*/i.test(q);
        var desired = 'Câu ' + lvl + ': ';
        if (!hasPrefix) {
            q = desired + q;
        } else if (!window.__EDUPLAY_QUICK_PREVIEW_SINGLE_QUESTION) {
            q = q.replace(/^(?:(?:câu|cau|question|q|pregunta|frage)\s*(?:hỏi|hoi|so)?(?:\s+số)?\s*\d+\s*[:.\-]?\s*)/i, desired);
        }
    } catch(e) {}
    var a = [qObj.correct_answer, qObj.incorrect_answers[0], qObj.incorrect_answers[1], qObj.incorrect_answers[2], ]

    aMix = shuffle(a);

    $('#card').fadeOut()

    setTimeout($.proxy(function () {
        qText.html(q);
        a1Text.html(aMix[0]);
        a2Text.html(aMix[1]);
        a3Text.html(aMix[2]);
        a4Text.html(aMix[3]);
        $('#card').fadeIn();
        playMillionaireQuestionEntrance();
        timerID = $('#timer');
        clearMillionaireAnswerPending();
        setMillionaireAnswerInteractivity(true);
        try {
            var tval = parseInt(qObj.time_limit || (window.DEFAULT_QUESTION_TIME || 60), 10);
            try { var tel = document.getElementById('timer'); if (tel) tel.setAttribute('data-timer', String(tval)); } catch(_){}
            try { timerID.data && timerID.data('timer', String(tval)); } catch(_){}
            try {
                if (window.__EP_TIMER_RESUME_TIMEOUT) {
                    clearTimeout(window.__EP_TIMER_RESUME_TIMEOUT);
                    window.__EP_TIMER_RESUME_TIMEOUT = null;
                }
            } catch(_clr){}
            try {
                var api = $('#timer').TimeCircles();
                if (api && api.stop) api.stop();
                setMillionaireAnswerInteractivity(false);
                lockMillionaireTimer(950);
                var restartTimer = function(){
                    try {
                        if (shouldKeepMillionaireTimerStopped()) {
                            return;
                        }
                        var a = $('#timer').TimeCircles();
                        if (a && a.stop) a.stop();
                        if (a && a.restart) a.restart();
                    } catch(_r){}
                    clearMillionaireTimerLock();
                    setMillionaireAnswerInteractivity(false);
                };
                var resumeDelay = 0;
                try {
                    var lockUntil = parseInt(window.__EP_SCORE_CUTSCENE_UNTIL || 0, 10);
                    if (lockUntil > 0) {
                        resumeDelay = Math.max(0, lockUntil - Date.now());
                    }
                } catch(_d){}
                resumeDelay = Math.max(resumeDelay, getMillionaireTimerLockRemaining());
                if (resumeDelay > 0) {
                    window.__EP_TIMER_RESUME_TIMEOUT = setTimeout(restartTimer, resumeDelay + 50);
                } else {
                    restartTimer();
                }
            } catch(_){}
            try {
                var v = document.querySelector('#timer .tc-value');
                if (v) { v.textContent = String(tval); }
            } catch(_){}
        } catch(_){}
        timerID.removeClass('hide');
        timerID.addClass('show');
        initTimer();
    }, this), 500);
}

//CHECK SELECTED ANSWER AGAINST ACTUAL ANSWER.
function checkAnswer(r, a) {

    if (r === a) {

        return true;
    } else {
        return false;
    }

}

function showExplanation(correctAnswer, questionObj) {
    try { console.log('[EP] showExplanation'); } catch(e){}
    var sx = 0, sy = 0;
    try {
        sx = window.pageXOffset || document.documentElement.scrollLeft || 0;
        sy = window.pageYOffset || document.documentElement.scrollTop || 0;
    } catch(_){}
    var blkEl = document.getElementById('explanationBlock');
    if (!blkEl) {
        try {
            var parent = document.getElementById('answerBlock') || document.getElementById('gameWindow') || document.body;
            var wrap = document.createElement('div');
            wrap.id = 'explanationBlock';
            wrap.className = 'explanationBlock';
            wrap.innerHTML = '<div class="explanationBox" id="explanationBox"><div id="explanationText"></div><button id="continueButton" class="continue-button">Tiếp tục</button></div>';
            parent.appendChild(wrap);
        } catch(e){}
    }
    var explanationText = $('#explanationText');
    var explanationBlock = $('#explanationBlock');
    var continueButton = $('#continueButton');
    try { 
        var blk0 = document.getElementById('explanationBlock'); 
        if (blk0) { 
            blk0.style.visibility = 'hidden'; 
            blk0.style.opacity = '0'; 
            blk0.style.display = 'block';
        }
    } catch(e){}
    try {
        if (document && document.documentElement && document.documentElement.style) {
            document.documentElement.style.setProperty('overflow-anchor', 'none');
        }
    } catch(_){}
    try { var timerID = $('#timer'); toggleShowHide(timerID); } catch(e){}
    try {
        if (questionObj && questionObj.explanation) {
            explanationText.html(String(questionObj.explanation));
        } else if (correctAnswer) {
            explanationText.html("Đáp án đúng là: " + String(correctAnswer));
        } else {
            explanationText.html("Xin lỗi, không có thông tin giải thích.");
        }
    } catch(e) {
        try { explanationText.text(String(correctAnswer||"")); } catch(_) {}
    }
    try {
        function placeExplanationBelowAnswers() {
            var blk = document.getElementById('explanationBlock');
            if (!blk) return;
            var gw = document.getElementById('gameWindow') || document.body;
            var layoutHost = document.getElementById('answerBlock') || gw;
            if (blk.parentNode !== layoutHost) { try { layoutHost.appendChild(blk); } catch(_){} }
            try {
                if (layoutHost && (!layoutHost.style.position || layoutHost.style.position === '')) {
                    layoutHost.style.position = 'relative';
                }
            } catch(_){}
            var ansBottom = 0;
            var scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
            var gwTop = 0;
            try {
                var gwRect = layoutHost.getBoundingClientRect();
                gwTop = (gwRect.top || 0) + scrollY;
            } catch(_){}
            try {
                ['ans1B', 'ans2B', 'ans3B', 'ans4B'].forEach(function(id){
                    var el = document.getElementById(id);
                    if (!el || el.offsetParent === null) return;
                    var rect = el.getBoundingClientRect();
                    ansBottom = Math.max(ansBottom, (rect.bottom || 0) + scrollY);
                });
            } catch(_){}
            if (!ansBottom) {
                try {
                    var qBlock = document.getElementById('questionBlock');
                    if (qBlock) {
                        var qRect = qBlock.getBoundingClientRect();
                        ansBottom = ((qRect.bottom || 0) + scrollY) + 94;
                    }
                } catch(_){}
            }
            var margin = 8;
            blk.style.position = 'absolute';
            blk.style.left = '50%';
            blk.style.right = '';
            blk.style.bottom = '';
            blk.style.top = '0px';
            blk.style.transform = 'translateX(-50%)';
            blk.style.margin = '0';
            blk.style.width = '72%';
            blk.style.maxWidth = '760px';
            blk.style.zIndex = '800';
            blk.style.pointerEvents = 'auto';
            var boxEl = document.getElementById('explanationBox');
            var textEl = document.getElementById('explanationText');
            var targetHeight = 0;
            if (boxEl) {
                boxEl.style.maxHeight = 'none';
                boxEl.style.overflow = 'visible';
            }
            if (textEl) {
                textEl.style.maxHeight = 'none';
                textEl.style.overflowY = 'visible';
            }
            try {
                var naturalBoxHeight = boxEl ? boxEl.scrollHeight : 200;
                targetHeight = Math.max(120, naturalBoxHeight);
                blk.style.maxHeight = targetHeight + 'px';
                if (boxEl) {
                    boxEl.style.maxHeight = targetHeight + 'px';
                }
            } catch(_h) {
                targetHeight = Math.max(160, boxEl ? (boxEl.scrollHeight || 0) : 160);
                blk.style.maxHeight = targetHeight + 'px';
                if (boxEl) { boxEl.style.maxHeight = targetHeight + 'px'; }
                if (textEl) {
                    textEl.style.maxHeight = 'none';
                    textEl.style.overflowY = 'visible';
                }
            }
            var actualBlockHeight = 0;
            try {
                actualBlockHeight = Math.max(
                    blk ? (blk.offsetHeight || 0) : 0,
                    boxEl ? (boxEl.offsetHeight || 0) : 0
                );
            } catch(_ah){}
            if (!actualBlockHeight || actualBlockHeight < 60) {
                actualBlockHeight = targetHeight;
            }
            try {
                var topDoc = ansBottom + margin;
                var topPx = Math.max(margin, Math.round(topDoc - gwTop));
                blk.style.top = topPx + 'px';
            } catch(_p) {
                blk.style.top = Math.max(margin, Math.round(ansBottom - gwTop + margin)) + 'px';
            }
            try {
                // Extend answer host exactly to include explanation block + footer safe area.
                var footerHeight = 64;
                var footerEl = document.querySelector('footer');
                if (footerEl) {
                    var footerRect = footerEl.getBoundingClientRect();
                    if (footerRect && isFinite(footerRect.height)) {
                        footerHeight = Math.ceil(footerRect.height || footerHeight);
                    }
                }
                if (layoutHost) {
                    if (layoutHost.__epBasePaddingBottom === undefined) {
                        layoutHost.__epBasePaddingBottom = layoutHost.style.paddingBottom || '';
                    }
                    if (layoutHost.__epBasePaddingBottomPx === undefined) {
                        var padPx = 0;
                        try {
                            padPx = parseFloat(window.getComputedStyle(layoutHost).paddingBottom) || 0;
                        } catch(_cp){}
                        layoutHost.__epBasePaddingBottomPx = padPx;
                    }
                    var blkTopWithinHost = parseFloat(blk.style.top || '0') || 0;
                    var neededPad = Math.ceil(blkTopWithinHost + actualBlockHeight + footerHeight + margin);
                    var newPad = Math.max(Math.ceil(layoutHost.__epBasePaddingBottomPx || 0), neededPad);
                    layoutHost.style.paddingBottom = newPad + 'px';
                }
            } catch(_){}
            blk.style.visibility = 'visible';
            blk.style.opacity = '1';
        }
        placeExplanationBelowAnswers();
        try { } catch(_t){}
        window.__EP_EXPL_PLACE = placeExplanationBelowAnswers;
        try { window.addEventListener('resize', placeExplanationBelowAnswers, { passive: true }); } catch(_){}
    } catch(e){}
    try { explanationBlock.show(); } catch(e){}
    try { continueButton.show(); } catch(e){}
    try {
        var blk = document.getElementById('explanationBlock');
        if (blk) {
            blk.style.pointerEvents = 'auto';
            blk.style.display = 'block';
            blk.style.visibility = 'visible';
            blk.style.opacity = '1';
            try { blk.scrollIntoView({ behavior: 'smooth', block: 'end' }); } catch(_s){}
            try {
                var rect = blk.getBoundingClientRect();
                var scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
                var targetY = scrollY + rect.bottom - window.innerHeight + 80;
                if (targetY > scrollY) { window.scrollTo({ top: targetY, behavior: 'smooth' }); }
            } catch(_s2){}
        }
    } catch(e){}
    try { /* allow user to scroll naturally */ } catch(_a){}
    continueButton.off('click').on('click', function() {
        try { explanationBlock.hide(); } catch(e){}
        try {
            var blk2 = document.getElementById('explanationBlock');
            if (blk2) {
                blk2.style.top = '';
                blk2.style.maxHeight = '';
                blk2.style.position = '';
            }
            var box2 = document.getElementById('explanationBox');
            if (box2) {
                box2.style.maxHeight = '';
                box2.style.overflow = '';
            }
            var txt2 = document.getElementById('explanationText');
            if (txt2) {
                txt2.style.maxHeight = '';
                txt2.style.overflowY = '';
            }
            var host2 = document.getElementById('answerBlock');
            if (host2 && host2.__epBasePaddingBottom !== undefined) {
                host2.style.paddingBottom = host2.__epBasePaddingBottom;
                delete host2.__epBasePaddingBottom;
                if (host2.__epBasePaddingBottomPx !== undefined) {
                    delete host2.__epBasePaddingBottomPx;
                }
            }
        } catch(e){}
        try {
            if (window.__EP_EXPL_PLACE) {
                try { window.removeEventListener('resize', window.__EP_EXPL_PLACE); }catch(_r){}
                window.__EP_EXPL_PLACE = null;
            }
        } catch(e){}
        try {
            if (document && document.documentElement && document.documentElement.style) {
                document.documentElement.style.removeProperty('overflow-anchor');
            }
        } catch(_d){}
        setTimeout(function() {
            try {
                if (typeof window !== 'undefined' && window.__EP_WRONG && !isMillionaireTeachingMode()) {
                    try { $('#timer').TimeCircles().stop(); } catch(e){}
                    showGameOverCutScene(parseInt(window.__EP_GAMEOVER_LEVEL || 0, 10));
                    window.__EP_WRONG = false;
                    return;
                }
                if (typeof window !== 'undefined' && typeof window.__EP_NEXT === 'function') {
                    try { $('#timer').TimeCircles().stop(); } catch(e){}
                    try { window.__EP_WRONG = false; } catch(ex) {}
                    window.__EP_NEXT();
                    return;
                }
            } catch (e) {}
            try {
                advanceToNextQuestion();
            } catch (e) {}
        }, 80);
    });
}

// Function to advance to the next question
function advanceToNextQuestion() {
    currentLevel++;
    actualLevel = (typeof actualLevel === 'number') ? (actualLevel + 1) : currentLevel;
    try {
        if (typeof questions !== 'undefined' && Array.isArray(questions)) {
            if (currentLevel > questions.length) {
                console.log("End of questions");
                return;
            }
            setLevel(actualLevel);
            loadQuestion(questions[currentLevel - 1]);
            if (typeof window !== 'undefined' && typeof window.enableClick === 'function') {
                window.enableClick();
            } else {
                try { enableClick(); } catch (e) {}
            }
        } else if (typeof window !== 'undefined' && typeof window.__EP_NEXT === 'function') {
            window.__EP_NEXT();
        }
    } catch (e) {
        try { console.warn('advanceToNextQuestion failed', e); } catch(_) {}
    }
}
