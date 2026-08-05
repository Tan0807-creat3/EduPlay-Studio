$( window ).on('load', function() {
  $('#preloader').fadeOut();
 

});

//Settings & Variables
var introVideo = document.getElementById('introVideo');
var footer = $('footer'); //  FOOTER
var mainMenu = $('#mainMenu'); // MAIN MENU SECTION
var gameWindow = $('#gameWindow'); // GAME WINDOW SECTION
var fadeTime = 1000;
mainMenu.hide();
var currentLevel = 1;
var actualLevel = 1;
var swichLevel = false;
var qty = 15;// align to WWBM 15 questions
var aMix = [];
var finalScore;


$(document).ready(function (){



var levelDOM = $('#currentLevel');
var actualDOM = $('#actualLevel');

$('#card').hide();
$('#AsktheAudience').hide();
$('#scoreCutScene').hide();
$('#addToLeaderboardBtn').hide();
$('#leaderboard').hide();
$('#scoreBtn').hide();


$('#endGameCutScene').hide(); //Change to Play
mainMenu.fadeIn(2000);

$('#timer').TimeCircles({
  "animation": "ticks",
  "bg_width": 0.1,
  "fg_width": 0.023333333333333334,
  "circle_bg_color": "#ffffff",
  "text_color": "#ffffff",
  "time": {
      "Days": {
          "text": "Days",
          "color": "#CCCCCC",
          "show": false
      },
      "Hours": {
          "show": false
      },
      "Minutes": {
          "show": false
      },
      "Seconds": {
          "text": "Time",
          "color": "#E3AB28",
          "show": true
      }
  }
});
$('#timer').TimeCircles().stop();


$('#introVideo').hide(); // Hide initial game intro video.

//-----------------------------------
//SWITCH COMMENTS TO SHOW MAIN MENU
//-----------------------------------

gameWindow.hide();
//mainMenu.hide();
//gameWindow.show();
//introComplete();

$('#playGameBtn').click(function () {
  footer.fadeOut(fadeTime); // fade out footer
  mainMenu.fadeOut(fadeTime); // fade out main menu
  $('#introVideo').fadeIn(); // fade in intro video
  introVideo.play(); // play intro video

  document.getElementById('introVideo').addEventListener('ended', function () {
    setTimeout($.proxy(function () {
      introComplete();
    }, this), fadeTime);
  }, false); // add listener for introVideo to end and call function.

});

$('#showLeaderboardBtn').on('click',function (){
  $('#leaderboard').fadeIn();
});

$('#exitLeaderboardBtn').on('click',function() {
  $('#leaderboard').fadeOut();
});

$('#volumeOff').on('click', function () { audioVolume(0); });
$('#volumeHalf').on('click', function () { audioVolume(0.3); });
$('#volumeOn').on('click', function () { audioVolume(1); });



function introComplete(e) {
  footer.fadeIn(fadeTime);
  $('#introVideo').fadeOut();
  gameWindow.fadeIn(fadeTime);
  
  initGame();
}

//Initialise Game

function initGame() {
  var questions = []; // QUESTION BANK ARRAY

  playMusic(currentLevel - 1);

  $('#scoreValue').prop('number', 1000000).animateNumber({
    number: 0,
    numberStep: function (now, tween) {
      var target = $(tween.elem),
        rounded_now = Math.round(now);
    }
  }, 1000, 'linear');

  var timer = $('#timer');

  var answer = $('#answer');
  var qObj = {};
  var source = Array.isArray(window.EDU_QUESTIONS) ? window.EDU_QUESTIONS.slice(0, qty) : [];
  for (i = 0; i < source.length; i++) {
    answer.html(source[i].correct_answer);
    var cAns = answer.text();
    qObj = {
      question: source[i].question,
      correct_answer: cAns,
      incorrect_answers: source[i].incorrect_answers,
      time_limit: parseInt(source[i].time_limit || (window.DEFAULT_QUESTION_TIME || 60), 10),
      explanation: (source[i].explanation || source[i].explain || "")
    };
    questions.push(qObj);
  }
  questions = shuffle(questions);
    // console.log(questions);

    //Load Initial Question and Set Level to 1
    setLevel(currentLevel);
    loadQuestion(questions[currentLevel - 1]);
    answerOneBtn();
    answerTwoBtn();
    answerThreeBtn();
    answerFourBtn();

    $('#ll5050').one('click', function () {
      playEffect("blast");
      $('#cross2').prop('hidden', false);
      var inc = questions[currentLevel - 1].incorrect_answers.slice(0,2);
      try {
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
            if (t && b){
              var txt = String((t.textContent||'')).trim();
              if (inc.indexOf(txt) !== -1){
                $(b).fadeOut();
              }
            }
          }catch(_){}
        });
      } catch(_){}
    });

    $('#llAudience').one('click', function () {
      playEffect("blast");
      $('#cross3').prop('hidden', false);
      $('#AsktheAudience').fadeIn(1000);
      var meter_values = [0, 0, 0, 0];
      var correct_answer = questions[currentLevel - 1].correct_answer;
      var a1 = aMix.indexOf(correct_answer);
      var a2 = aMix.indexOf(questions[currentLevel - 1].incorrect_answers[0]);
      var a3 = aMix.indexOf(questions[currentLevel - 1].incorrect_answers[1]);
      var a4 = aMix.indexOf(questions[currentLevel - 1].incorrect_answers[2]);
      var pos1 = getRndInteger(60, 100);
      meter_values[a1] = pos1;
      var rem1 = 100 - pos1;
      var pos2 = getRndInteger(10, rem1);
      meter_values[a2] = pos2;
      var rem2 = rem1 - pos2;
      var pos3 = getRndInteger(10, rem2);
      meter_values[a3] = pos3;
      var rem3 = rem2 - pos3;
      var pos4 = getRndInteger(10, rem3);
      meter_values[a4] = pos4;
      setAudienceMeters(meter_values[0], meter_values[1], meter_values[2], meter_values[3]);
    });

    $('#llSwitch').one('click', function () {
      playEffect("blast");
      $('#cross1').prop('hidden', false);
      loadNextOrEnd();
    });



    function isMillionaireTeachingMode() {
      try {
        var mode = window.EDU_MILLIONAIRE_MODE || window.__EP_MILLIONAIRE_MODE || (((window.EDU_PROJECT || {}).game_config || {}).export_mode) || 'student';
        return String(mode || 'student').toLowerCase() === 'teaching';
      } catch (e) {
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

    function getMillionaireCutsceneDelay() {
      try {
        var lockUntil = parseInt(window.__EP_SCORE_CUTSCENE_UNTIL || 0, 10);
        return Math.max(0, lockUntil - Date.now());
      } catch(e) {
        return 0;
      }
    }

    function bindAnswerHandler(blockSelector, textSelector) {
      $(blockSelector).off('click');
      if (isMillionaireTeachingMode()) {
        $(blockSelector).on('click', function () {
          if (this && this.classList && (this.classList.contains('locked') || this.classList.contains('answerIncorrect'))) {
            return;
          }
          var r = $(textSelector).html();
          var a = decodeURI(questions[currentLevel - 1].correct_answer);
          var q = questions[currentLevel - 1];
          markMillionaireAnswerPending();
          highLightAnswerOrange(this.id);
          if (checkAnswer(r, a)) {
            disableClick();
            window.__EP_WRONG = false;
            highLightAnswerGreen(this, a, q);
          } else {
            window.__EP_WRONG = false;
            highLightAnswerRed(this, a, q);
          }
        });
        return;
      }
      $(blockSelector).one('click', function () {
        disableClick();
        var r = $(textSelector).html();
        var a = decodeURI(questions[currentLevel - 1].correct_answer);
        var q = questions[currentLevel - 1];
        markMillionaireAnswerPending();
        highLightAnswerOrange(this.id);
        if (checkAnswer(r, a)) {
          window.__EP_WRONG = false;
          highLightAnswerGreen(this, a, q);
        } else {
          window.__EP_WRONG = true;
          window.__EP_GAMEOVER_LEVEL = actualLevel - 1;
          highLightAnswerRed(this, a, q);
        }
      });
    }

    window.enableClick = function () {
      answerOneBtn();
      answerTwoBtn();
      answerThreeBtn();
      answerFourBtn();
    }

    function loadNextOrEnd() {
      // Move to the next level before loading question
      currentLevel += 1;
      actualLevel += 1;
      var nextIndex = currentLevel - 1;
      if (!Array.isArray(questions) || nextIndex >= questions.length) {
        gameOver(actualLevel);
        return;
      }
      var proceedToNextQuestion = function () {
        try {
          var scoreCutScene = document.getElementById('scoreCutScene');
          if (scoreCutScene && scoreCutScene.offsetParent !== null) {
            if (window.__EP_NEXT_QUESTION_TIMEOUT) {
              clearTimeout(window.__EP_NEXT_QUESTION_TIMEOUT);
            }
            window.__EP_NEXT_QUESTION_TIMEOUT = setTimeout(proceedToNextQuestion, 200);
            return;
          }
        } catch(_guard) {}
        try {
          if (window.__EP_NEXT_QUESTION_TIMEOUT) {
            clearTimeout(window.__EP_NEXT_QUESTION_TIMEOUT);
            window.__EP_NEXT_QUESTION_TIMEOUT = null;
          }
        } catch(_clear) {}
        highlightAnswerReset();
        loadQuestion(questions[nextIndex]);
        window.enableClick();
      };
      // Update UI state and only load the next question after any score cutscene ends.
      setLevel(actualLevel);
      checkCutScene(actualLevel);
      var cutsceneDelay = getMillionaireCutsceneDelay();
      if (cutsceneDelay > 0) {
        try { $('#timer').TimeCircles().stop(); } catch(e) {}
        try {
          if (window.__EP_NEXT_QUESTION_TIMEOUT) {
            clearTimeout(window.__EP_NEXT_QUESTION_TIMEOUT);
          }
          window.__EP_NEXT_QUESTION_TIMEOUT = setTimeout(proceedToNextQuestion, cutsceneDelay + 50);
        } catch(_delay) {
          proceedToNextQuestion();
        }
        return;
      }
      proceedToNextQuestion();
    }
    window.__EP_NEXT = loadNextOrEnd;



    function answerOneBtn() {
      bindAnswerHandler('#ans1B', '#ans1');
    }



    function answerTwoBtn() {
      bindAnswerHandler('#ans2B', '#ans2');
    }


    function answerThreeBtn() {
      bindAnswerHandler('#ans3B', '#ans3');
    }


    function answerFourBtn() {
      bindAnswerHandler('#ans4B', '#ans4');
    }

     //gameOver(15);
}
window.initGame = initGame;
// -------------------------


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

//Reset background colours on answer buttons.
function highlightAnswerReset() {
    $('#ans1B, #ans2B, #ans3B, #ans4B')
        .removeClass('answerCorrect answerIncorrect answerCheck')
        .addClass('answer')
        .removeClass('locked')
        .show();
    try { stopEffect("finalAnswer"); } catch(e){}
    try { stopEffect("wrongAnswer"); } catch(e){}
    try { stopEffect(currentEffect); } catch(e){}
    try { $('#timer').TimeCircles().stop(); } catch(e){}
    try { ['ans1B','ans2B','ans3B','ans4B'].forEach(function(id){ var el=document.getElementById(id); if(el){ el.style.pointerEvents=''; } }); } catch(e){}
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
function highLightAnswerOrange(id) {
    //$('#' + id).html('123');
    stopMusic(actualLevel - 1);
    playEffect("finalAnswer");
    $('#timer').TimeCircles().stop();
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
    }, this), 4000);
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
    }, this), 3000);
}

//SEARCH FOR CORRECT ANSWER AND HIGHLIGHT
function highlightCorrectAnswer(ans) {
    $("#ans1B:contains('" + ans + "')").removeClass('answerCheck').addClass('answerCorrect');
    $("#ans2B:contains('" + ans + "')").removeClass('answerCheck').addClass('answerCorrect');
    $("#ans3B:contains('" + ans + "')").removeClass('answerCheck').addClass('answerCorrect');
    $("#ans4B:contains('" + ans + "')").removeClass('answerCheck').addClass('answerCorrect');
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
    try {
        if (window.__EP_TIMER_RESUME_TIMEOUT) {
            clearTimeout(window.__EP_TIMER_RESUME_TIMEOUT);
            window.__EP_TIMER_RESUME_TIMEOUT = null;
        }
    } catch(e) {}
    try { $('#timer').TimeCircles().stop(); } catch(e) {}
    try { window.__EP_SCORE_CUTSCENE_UNTIL = Date.now() + 7500; } catch(e) {}
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
        try { window.__EP_SCORE_CUTSCENE_UNTIL = 0; } catch(e) {}
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

function resetToHome(){
    try{ stopEffect(currentEffect); }catch(e){}
    try{ stopMusic(actualLevel - 1); }catch(e){}
    try{ $('#timer').TimeCircles().stop(); }catch(e){}
    $('#endGameCutScene').hide();
    $('#leaderboard').hide();
    $('#gameWindow').hide();
    $('footer').fadeIn(500);
    $('#mainMenu').fadeIn(500);
    currentLevel = 1;
    actualLevel = 1;
    $('#exitGameBtn').hide();
}

function initTimer() {
    var timer = $('#timer');
    timer.TimeCircles().addListener(function () {
        if (window.__EP_ANSWER_PENDING) {
            try { timer.TimeCircles().stop(); } catch(e) {}
            return;
        }
        var time = timer.TimeCircles().getTime()
        if (time < 1) {
            timer.TimeCircles().stop();
            timer.data('timer', 0);
            try { window.__EP_ANSWER_PENDING = false; } catch(e) {}
            stopMusic(actualLevel - 1);
            playEffect("wrongAnswer");
            try{ stopEffect("ticktock"); window.__ticktockPlaying = false; }catch(e){}
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
    $('#endGameHeader').text(pickRandomMessage(isWinner ? winMessages : loseMessages));
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
    console.log("Correct Answer - " + unescape(qObj.correct_answer));
    var qText = $('#question');
    var a1Text = $('#ans1');
    var a2Text = $('#ans2');
    var a3Text = $('#ans3');
    var a4Text = $('#ans4');

    var q = qObj.question; // set question
    var a = [qObj.correct_answer, qObj.incorrect_answers[0], qObj.incorrect_answers[1], qObj.incorrect_answers[2], ]

    aMix = shuffle(a);

    $('#card').fadeOut()

    setTimeout($.proxy(function () {
        try {
          var s = String(q || '');
          s = s.replace(/^(?:(?:câu|cau|question|q|pregunta|frage)\s*(?:hỏi|hoi|so)?(?:\s+số)?\s*\d+\s*[:.\-]?\s*)/i, '');
          q = 'Câu ' + actualLevel + ': ' + s;
        } catch(e){}
        qText.html(q);
        a1Text.html(aMix[0]);
        a2Text.html(aMix[1]);
        a3Text.html(aMix[2]);
        a4Text.html(aMix[3]);
        $('#card').fadeIn();
        timerID = $('#timer');
        clearMillionaireAnswerPending();
        var tl = parseInt(qObj.time_limit || (window.DEFAULT_QUESTION_TIME || 60), 10);
        timerID.data('timer', tl);
        try {
            if (window.__EP_TIMER_RESUME_TIMEOUT) {
                clearTimeout(window.__EP_TIMER_RESUME_TIMEOUT);
                window.__EP_TIMER_RESUME_TIMEOUT = null;
            }
        } catch(e) {}
        try {
            timerID.TimeCircles().stop();
            var resumeDelay = getMillionaireCutsceneDelay();
            var restartTimer = function() {
                try {
                    var scoreCutScene = document.getElementById('scoreCutScene');
                    if (scoreCutScene && scoreCutScene.offsetParent !== null) {
                        return;
                    }
                } catch(_guard) {}
                try { timerID.TimeCircles().restart(); } catch(_restart) {}
            };
            if (resumeDelay > 0) {
                window.__EP_TIMER_RESUME_TIMEOUT = setTimeout(function() {
                    window.__EP_TIMER_RESUME_TIMEOUT = null;
                    restartTimer();
                }, resumeDelay + 50);
            } else {
                restartTimer();
            }
        } catch(e) {
            try { timerID.TimeCircles().restart(); } catch(_fallback) {}
        }
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









});
