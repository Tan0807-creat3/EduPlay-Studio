//sounds.js

// text to speech - https://codepen.io/SteveJRobertson/pen/emGWaR

/*
------------------------------------
Music Tracks (use playMusic(<track #) stopMusic(<track #) )
------------------------------------
Track 0 - 0 to 1,000
Track 1 - 2,000 to 32,000
Track 2 - 64,000
Track 3 - 125,000 to 250,000
Track 4 - 500,000
Track 5 - 1,000,000
------------------------------------
Sound Effects (use playEffect("") stopEffect("") )
------------------------------------
Correct Answer - correctAnswer
Final Answer - finalAnswer
Begin Game - beginGame1
Begin Game(2) - beginGame2
Phone A Friend - phoneFriend
Wrong Answer - wrongAnswer
------------------------------------
*/
var currentEffect;
var millionaireFeedbackPools = { correct: null, wrong: null };
var millionaireFeedbackLastIndex = { correct: -1, wrong: -1 };

function normalizeMillionaireFeedbackText(text) {
    try {
        return String(text || '').replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim();
    } catch (e) {
        return '';
    }
}

function createMillionaireFeedbackEntry(item) {
    try {
        if (!item) return null;
        var src = typeof item === 'string' ? item : (item.src || item.audio || item.url || '');
        if (!src) return null;
        var audio = new Audio(src);
        audio.preload = 'auto';
        return {
            src: src,
            text: normalizeMillionaireFeedbackText(typeof item === 'string' ? '' : (item.text || item.label || item.name || '')),
            audio: audio
        };
    } catch (e) {
        return null;
    }
}

function initMillionaireFeedbackPools() {
    millionaireFeedbackPools.correct = [];
    millionaireFeedbackPools.wrong = [];
}

function getMillionaireEffectVolume() {
    try {
        var soundEffects = $('audio#effects');
        var first = soundEffects && soundEffects[0];
        var volume = Number(first && first.volume);
        if (isFinite(volume) && volume >= 0) return volume;
    } catch (e) {}
    return 1;
}

function pickMillionaireFeedbackEntry(kind) {
    try {
        initMillionaireFeedbackPools();
        var pool = millionaireFeedbackPools[kind] || [];
        if (!pool.length) return null;
        if (pool.length === 1) {
            millionaireFeedbackLastIndex[kind] = 0;
            return pool[0];
        }
        var nextIndex = Math.floor(Math.random() * pool.length);
        if (nextIndex === millionaireFeedbackLastIndex[kind]) {
            nextIndex = (nextIndex + 1 + Math.floor(Math.random() * (pool.length - 1))) % pool.length;
        }
        millionaireFeedbackLastIndex[kind] = nextIndex;
        return pool[nextIndex];
    } catch (e) {
        return null;
    }
}

function playMillionaireFeedbackPool(kind) {
    try {
        var entry = pickMillionaireFeedbackEntry(kind);
        if (!entry || !entry.audio) return false;
        try { entry.audio.pause(); } catch (e) {}
        try { entry.audio.currentTime = 0; } catch (e) {}
        try { entry.audio.volume = getMillionaireEffectVolume(); } catch (e) {}
        var played = entry.audio.play();
        if (played && played.catch) played.catch(function(){});
        return true;
    } catch (e) {
        return false;
    }
}

function stopMillionaireFeedbackPool(kind) {
    try {
        initMillionaireFeedbackPools();
        var pool = millionaireFeedbackPools[kind] || [];
        pool.forEach(function(entry) {
            try {
                if (entry && entry.audio) {
                    entry.audio.pause();
                    entry.audio.currentTime = 0;
                }
            } catch (e) {}
        });
    } catch (e) {}
}



//   sound.play();



function audioVolume(x) {
    var backgroundMusic = $('audio#music');
    var soundEffects = $('audio#effects');
    backgroundMusic.prop("volume",x);
    soundEffects.prop("volume",x);
}

function playMusic(track) {
    var backgroundMusic = $('audio#music');


    var music;
    switch (track) {
        case 0: // $0
        case 1: // $100
        case 2: // $250
        case 3: // $500
        case 4: // $1,000
            music = 0;
            break;
        case 5: // $2,000
        case 6: // $4,000
        case 7: // $8,000
        case 8: // $16,000
        case 9: // $32,000
            music = 1;
            break;
        case 10: // $64,000
            music = 2;
            break;
        case 11: // $125,000
        case 12: // $250,000
            music = 3;
            break;
        case 13: // $500,000
            music = 4;
            break;
        case 14: // $1,000,000
            music = 5;
            break;
        case 15:
            music = 5;
            break;
        case 16:
            music = 5;
            break;
        default:
            music = 0;
    }
    // console.log("Playing Track - " + music);

    try {
        var pm = backgroundMusic[music].play();
        if (pm && pm.catch) pm.catch(function(){});
    } catch(e) {}

}

function playEffect(track) {
    var soundEffects = $('audio#effects');
    currentEffect = track;
    switch (track) {
        case "correctAnswer":
            try{ var p0 = soundEffects[0].play(); if (p0 && p0.catch) p0.catch(function(){});}catch(e){}
            break;
        case "finalAnswer":
            try{ var p1 = soundEffects[1].play(); if (p1 && p1.catch) p1.catch(function(){});}catch(e){}
            break;
        case "beginGame2":
            try{ var p2 = soundEffects[2].play(); if (p2 && p2.catch) p2.catch(function(){});}catch(e){}
            break;
        case "phoneFriend":
            try{ var p3 = soundEffects[3].play(); if (p3 && p3.catch) p3.catch(function(){});}catch(e){}
            break;
        case "wrongAnswer":
            try{ var p4 = soundEffects[4].play(); if (p4 && p4.catch) p4.catch(function(){});}catch(e){}
            break;
        case "beginGame1":
            try{ var p5 = soundEffects[5].play(); if (p5 && p5.catch) p5.catch(function(){});}catch(e){}
            break;
        case "blast":
            try{ var p6 = soundEffects[6].play(); if (p6 && p6.catch) p6.catch(function(){});}catch(e){}
            break;
        case "winner":
            try{ var p7 = soundEffects[7].play(); if (p7 && p7.catch) p7.catch(function(){});}catch(e){}
            break;
        case "ticktock":
            try{ var p8 = soundEffects[8].play(); if (p8 && p8.catch) p8.catch(function(){});}catch(e){}
            break;
        default:
    }
    //console.log(currentEffect);

}

function stopMusic(track) {
    var backgroundMusic = $('audio#music');

    var music;
    switch (track) {
        case 0: // $0
        case 1: // $100
        case 2: // $250
        case 3: // $500
        case 4: // $1,000
            music = 0;
            break;
        case 5: // $2,000
        case 6: // $4,000
        case 7: // $8,000
        case 8: // $16,000
        case 9: // $32,000
            music = 1;
            break;
        case 10: // $64,000
            music = 2;
            break;
        case 11: // $125,000
        case 12: // $250,000
            music = 3;
            break;
        case 13: // $500,000
            music = 4;
            break;
        case 14: // $1,000,000
            music = 5;
            break;
        default:
            music = 0;
    }
    // console.log("Stoppping Track - " + music);
    backgroundMusic[music].pause();
    backgroundMusic[music].currentTime = 0;
}

function stopEffect(track) {
    currentEffect = "";
    var soundEffects = $('audio#effects');
    switch (track) {
        case "correctAnswer":
            stopMillionaireFeedbackPool("correct");
            soundEffects[0].pause();
            soundEffects[0].currentTime = 0;
            break;
        case "finalAnswer":
            soundEffects[1].pause();
            soundEffects[1].currentTime = 0;
            break;
        case "beginGame2":
            soundEffects[2].pause();
            soundEffects[2].currentTime = 0;
            break;
        case "phoneFriend":
            soundEffects[3].pause();
            soundEffects[3].currentTime = 0;
            break;
        case "wrongAnswer":
            stopMillionaireFeedbackPool("wrong");
            soundEffects[4].pause();
            soundEffects[4].currentTime = 0;
            break;
        case "beginGame1":
            soundEffects[5].pause();
            soundEffects[5].currentTime = 0;
            break;
        case "winner":
            soundEffects[7].pause();
            soundEffects[7].currentTime = 0;
            break;
        case "ticktock":
            soundEffects[8].pause();
            soundEffects[8].currentTime = 0;
            break;


        default:
    }
}
