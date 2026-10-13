/* Mimo — the learners interface. Talks to the public API. */
(function () {
  "use strict";

  var API = "/api/v1";
  var bot = document.getElementById("lmBot");
  var langBox = document.getElementById("lmLanguages");
  var statsBox = document.getElementById("lmStats");
  var wordBox = document.getElementById("lmWord");
  var leadersBox = document.getElementById("lmLeaders");
  var barsBox = document.getElementById("lmBars");
  var quizBox = document.getElementById("lmQuiz");
  var quizSection = document.getElementById("lmQuizSection");
  var dialectBox = document.getElementById("lmDialects");
  var speakChip = document.getElementById("lmSpeakChip");
  var chatLog = document.getElementById("lmChatLog");
  var chatReplies = document.getElementById("lmChatReplies");
  var chatForm = document.getElementById("lmChatForm");
  var chatInput = document.getElementById("lmChatInput");

  var state = { totals: null, languages: [], selected: null, selectedDialect: null,
    quiz: { correct: 0, total: 0, streak: 0 } };
  var talkTimer = null;
  var happyTimer = null;
  var sadTimer = null;

  // ------------------------------------------------------------- chat engine
  var sayQueue = [];
  var saying = false;

  function scrollChat() {
    if (chatLog) chatLog.scrollTop = chatLog.scrollHeight;
  }

  function addBubble(who, text) {
    if (!chatLog) return null;
    var bubble = el('<div class="lm-msg ' + who + '"></div>');
    bubble.textContent = text;
    chatLog.appendChild(bubble);
    scrollChat();
    return bubble;
  }

  function showTyping() {
    if (!chatLog) return null;
    var typing = el('<div class="lm-msg mimo typing"><span></span><span></span><span></span></div>');
    chatLog.appendChild(typing);
    scrollChat();
    return typing;
  }

  function removeTyping(node) {
    if (node && node.parentNode) node.parentNode.removeChild(node);
  }

  function mimoFeel(mood) {
    if (!bot) return;
    clearTimeout(happyTimer);
    clearTimeout(sadTimer);
    bot.classList.remove("is-happy", "is-sad");
    if (mood === "happy") {
      bot.classList.add("is-happy");
      happyTimer = setTimeout(function () { bot.classList.remove("is-happy"); }, 2200);
    } else if (mood === "sad") {
      bot.classList.add("is-sad");
      sadTimer = setTimeout(function () { bot.classList.remove("is-sad"); }, 2400);
    }
  }

  function deliver(item) {
    addBubble("mimo", item.text);
    if (bot) {
      bot.classList.add("is-talking");
      if (item.mood === "sad") {
        mimoFeel("sad");
      } else {
        mimoFeel("happy");
      }
      clearTimeout(talkTimer);
      talkTimer = setTimeout(function () {
        bot.classList.remove("is-talking");
      }, Math.min(2600, 420 + item.text.length * 28));
    }
    if (typeof item.after === "function") item.after();
  }

  function pump() {
    if (saying || !sayQueue.length) return;
    saying = true;
    var item = sayQueue.shift();
    var typing = showTyping();
    var delay = Math.min(1700, 480 + item.text.length * 20);
    setTimeout(function () {
      removeTyping(typing);
      deliver(item);
      saying = false;
      setTimeout(pump, 170);
    }, delay);
  }

  function mimoSay(text, opts) {
    opts = opts || {};
    sayQueue.push({ text: text, mood: opts.mood, after: opts.after });
    pump();
  }

  function setReplies(list) {
    if (!chatReplies) return;
    chatReplies.innerHTML = "";
    (list || []).forEach(function (item) {
      var chip = el('<button type="button" class="lm-reply"></button>');
      chip.textContent = item.label;
      chip.addEventListener("click", item.onClick);
      chatReplies.appendChild(chip);
    });
  }

  // ---------------------------------------------------------------- audio
  var SOUNDS = {
    intro: "/static/audio/mimo-intro.mp3",
    greeting: "/static/audio/mimo-greeting.mp3"
  };
  var muted = false;
  var greeted = false;
  var currentAudio = null;
  var soundBtn = document.getElementById("lmSound");
  var playBtn = document.getElementById("lmPlay");

  try { muted = localStorage.getItem("mimoMuted") === "1"; } catch (e) { muted = false; }

  function applySoundUi() {
    if (soundBtn) {
      soundBtn.textContent = muted ? "🔇" : "🔊";
      soundBtn.title = muted ? "Sound off" : "Sound on";
      soundBtn.classList.toggle("is-on", !muted);
      soundBtn.setAttribute("aria-pressed", muted ? "false" : "true");
    }
  }

  function setMuted(value) {
    muted = value;
    try { localStorage.setItem("mimoMuted", muted ? "1" : "0"); } catch (e) {}
    if (muted && currentAudio) currentAudio.pause();
    applySoundUi();
  }

  function playSound(name, fallback) {
    var src = SOUNDS[name];
    if (!src || muted) return;
    try {
      if (currentAudio) currentAudio.pause();
      var audio = new Audio(src);
      currentAudio = audio;
      var usedFallback = false;
      var start = function () { if (bot) bot.classList.add("is-speaking", "is-talking"); };
      var stop = function () { if (bot) bot.classList.remove("is-speaking", "is-talking"); };
      var useFallback = function () {
        if (fallback && !usedFallback) { usedFallback = true; playSound(fallback); }
        else { stop(); }
      };
      audio.addEventListener("play", start);
      audio.addEventListener("ended", stop);
      audio.addEventListener("error", useFallback);
      var started = audio.play();
      if (started && started.catch) started.catch(useFallback);
    } catch (e) { /* audio unsupported — stay silent */ }
  }

  function greetOnce() {
    if (greeted) return;
    greeted = true;
    // Use the snappy 3-second greeting; fall back to the full intro if absent.
    playSound("greeting", "intro");
  }

  // ---------------------------------------------------------------- Mimo eyes
  function blink() {
    var eyes = document.querySelectorAll(".lm-eye");
    eyes.forEach(function (e) { e.classList.add("lm-blink"); });
    setTimeout(function () {
      eyes.forEach(function (e) { e.classList.remove("lm-blink"); });
    }, 170);
  }

  function scheduleBlink() {
    var delay = 2200 + Math.random() * 4200;
    setTimeout(function () { blink(); scheduleBlink(); }, delay);
  }

  function trackEyes(clientX, clientY) {
    var pupils = document.querySelectorAll("[data-pupil]");
    pupils.forEach(function (pupil) {
      var r = pupil.parentElement.getBoundingClientRect();
      var cx = r.left + r.width / 2;
      var cy = r.top + r.height / 2;
      var dx = clientX - cx;
      var dy = clientY - cy;
      var len = Math.sqrt(dx * dx + dy * dy) || 1;
      var max = r.width * 0.22;
      var ox = (dx / len) * Math.min(max, (Math.abs(dx) / 14));
      var oy = (dy / len) * Math.min(max, (Math.abs(dy) / 14));
      pupil.style.transform = "translate(" + ox.toFixed(1) + "px," + oy.toFixed(1) + "px)";
    });
  }

  // ------------------------------------------------------------- helpers
  function el(html) {
    var t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function countUp(node, target) {
    var duration = 900;
    var start = performance.now();
    function frame(now) {
      var p = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - p, 3);
      node.textContent = Math.round(target * eased).toLocaleString();
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function findLanguage(text) {
    var t = String(text || "").toLowerCase();
    for (var i = 0; i < state.languages.length; i++) {
      var lang = state.languages[i];
      var name = String(lang.name || "").toLowerCase();
      if (name && t.indexOf(name) !== -1) return lang;
      var native = String(lang.native_name || "").toLowerCase();
      if (native && t.indexOf(native) !== -1) return lang;
      if (name && t.length >= 4 && name.indexOf(t) !== -1) return lang;
    }
    return null;
  }

  // ---------------------------------------------------- Mimo's dialect
  // Mimo can "speak" a specific dialect when the community has content for it,
  // falling back to the whole language. Remembered per language in the browser.
  var dialectStore = {};
  try { dialectStore = JSON.parse(localStorage.getItem("mimoDialects") || "{}") || {}; }
  catch (e) { dialectStore = {}; }

  function rememberDialect(lang, dialect) {
    var key = String(lang.id);
    if (dialect) dialectStore[key] = dialect.id;
    else delete dialectStore[key];
    try { localStorage.setItem("mimoDialects", JSON.stringify(dialectStore)); } catch (e) {}
  }

  function rememberedDialect(lang) {
    var wanted = dialectStore[String(lang.id)];
    if (!wanted) return null;
    return (lang.dialects || []).filter(function (d) {
      return d.id === wanted || String(d.id) === String(wanted);
    })[0] || null;
  }

  function dialectQuery() {
    return state.selectedDialect
      ? "&dialect=" + encodeURIComponent(state.selectedDialect.name)
      : "";
  }

  function langLabel(lang) {
    lang = lang || state.selected;
    if (!lang) return "";
    return lang.name + (state.selectedDialect ? " · " + state.selectedDialect.name : "");
  }

  function updateSpeakChip() {
    if (!speakChip) return;
    if (!state.selected) { speakChip.hidden = true; return; }
    speakChip.hidden = false;
    speakChip.textContent = "🎙️ " + langLabel(state.selected);
  }

  function renderDialects(lang) {
    if (!dialectBox) return;
    var dialects = lang ? (lang.dialects || []) : [];
    if (!dialects.length) {
      dialectBox.hidden = true;
      dialectBox.innerHTML = "";
      return;
    }
    dialectBox.hidden = false;
    dialectBox.innerHTML = "";
    var all = [{ id: null, name: "Community-wide" }].concat(dialects);
    all.forEach(function (d) {
      var current = state.selectedDialect ? state.selectedDialect.id : null;
      var active = current === d.id || String(current) === String(d.id);
      var pill = el('<button type="button" class="lm-dialect' +
        (active ? " is-active" : "") + '">' + esc(d.name) + "</button>");
      pill.addEventListener("click", function () {
        setDialect(lang, d.id === null ? null : d);
      });
      dialectBox.appendChild(pill);
    });
  }

  function setDialect(lang, dialect) {
    state.selectedDialect = dialect;
    rememberDialect(lang, dialect);
    renderDialects(lang);
    updateSpeakChip();
    mimoSay(dialect
      ? "Sawa! I'll speak " + lang.name + " · " + dialect.name + " now. 🎙️"
      : "Back to community-wide " + lang.name + ". 🌍");
    loadWord(lang);
    startQuiz(lang);
    sendAwarenessTip(lang);
  }

  // ------------------------------------------------------------- render
  function renderStats(totals) {
    if (!statsBox) return;
    var cards = [
      ["languages_with_data", "language communities learning"],
      ["submissions", "community samples shared"],
      ["approved_translations", "verified translations"],
      ["assessments", "peer assessments"],
      ["registered_contributors", "registered contributors"]
    ];
    statsBox.innerHTML = "";
    cards.forEach(function (pair) {
      var card = el('<div class="lm-stat"><span class="lm-num">0</span><span class="lm-lbl">' +
        esc(pair[1]) + "</span></div>");
      statsBox.appendChild(card);
      countUp(card.querySelector(".lm-num"), totals[pair[0]] || 0);
    });
  }

  function renderLanguages(languages) {
    if (!langBox) return;
    langBox.innerHTML = "";
    var withData = languages.filter(function (l) { return l.submissions > 0; });
    (withData.length ? withData : languages).forEach(function (lang) {
      var pill = el('<button type="button" class="lm-pill">' +
        esc(lang.name) + ' <small>' + lang.submissions + " samples</small></button>");
      pill.dataset.lang = lang.name;
      pill.addEventListener("click", function () { chooseLanguage(lang); });
      langBox.appendChild(pill);
    });
  }

  function highlightPills(lang) {
    document.querySelectorAll(".lm-pill").forEach(function (p) {
      p.classList.toggle("is-active", p.dataset.lang === lang.name);
    });
  }

  function renderLeaders(top) {
    if (!leadersBox) return;
    leadersBox.innerHTML = "";
    if (!top || !top.length) {
      leadersBox.appendChild(el(
        '<li class="lm-loading">Our first stars are still rising — could be you! 🌟</li>'
      ));
      return;
    }
    top.forEach(function (row) {
      var initials = (row.contributor || "?").trim().split(/\s+/).map(function (w) {
        return w[0];
      }).join("").slice(0, 2).toUpperCase();
      leadersBox.appendChild(el(
        '<li>' +
          '<span class="lm-avatar">' + esc(initials) + "</span>" +
          '<span class="lm-who">' + esc(row.contributor) + "</span>" +
          '<span class="lm-meta"><strong>' + esc(row.tier) + "</strong><br>" +
          row.reputation + " rep · " + row.approved + " verified</span>" +
        "</li>"
      ));
    });
  }

  function renderBars(languages) {
    if (!barsBox) return;
    barsBox.innerHTML = "";
    var max = Math.max.apply(null, languages.map(function (l) { return l.submissions; }).concat([1]));
    languages.forEach(function (lang) {
      var pct = Math.round((lang.submissions / max) * 100);
      var row = el(
        '<div class="lm-bar-row">' +
          '<span class="lm-name">' + esc(lang.name) + "</span>" +
          '<span class="lm-bar"><span></span></span>' +
          '<span class="lm-count">' + lang.submissions + " words</span>" +
        "</div>"
      );
      barsBox.appendChild(row);
      setTimeout(function () {
        row.querySelector(".lm-bar > span").style.width = pct + "%";
      }, 120);
    });
  }

  // ---------------------------------------------------- word of the moment
  function loadWord(lang) {
    if (!wordBox) return;
    wordBox.innerHTML = '<p class="lm-loading">Mimo is fetching a ' + esc(langLabel(lang)) + " word…</p>";
    fetch("/learn/word?language=" + encodeURIComponent(lang.name) + dialectQuery() + "&category=glossary")
      .then(function (r) { return r.ok ? r.json() : { available: false }; })
      .then(function (data) {
        if (!data.available) {
          wordBox.innerHTML =
            '<div class="lm-word"><span class="lm-term">' + esc(langLabel(lang)) + "</span>" +
            '<div class="lm-trans">Be the first to teach Mimo a word! 🌱</div>' +
            '<div class="lm-def">No words for this language yet — ' +
            lang.submissions + " community samples are waiting for review.</div>" +
            '<a class="lm-badge" href="/tasks">Help verify one →</a></div>';
          return;
        }
        showWord(data.word, lang);
      })
      .catch(function () {
        wordBox.innerHTML = '<p class="lm-loading">Mimo had trouble reaching the word. Try another language?</p>';
      });
  }

  function showWord(w, lang) {
    wordBox.innerHTML =
      '<div class="lm-word">' +
        '<span class="lm-term">' + esc(w.term) + " · " + esc(langLabel(lang)) + "</span>" +
        '<div class="lm-trans">' + esc(w.translation) + "</div>" +
        '<div class="lm-def">' + esc(w.definition || "A cybersecurity word to know.") + "</div>" +
        '<span class="lm-badge">' + (w.verified ? "✓ community verified" : "🌱 community sample") + "</span>" +
      "</div>";
  }

  // ---------------------------------------------------------------- quiz
  function chips() {
    return '<span class="lm-chip">⭐ Score ' + state.quiz.correct + "/" + state.quiz.total + "</span>" +
      '<span class="lm-chip">🔥 Streak ' + state.quiz.streak + "</span>" +
      (state.selected ? '<span class="lm-chip">🌍 ' + esc(langLabel()) + "</span>" : "");
  }

  function startQuiz(lang) {
    if (!quizBox) return;
    quizBox.innerHTML = '<p class="lm-loading">Mimo is thinking of a question…</p>';
    fetch("/learn/quiz?language=" + encodeURIComponent(lang.name) + dialectQuery())
      .then(function (r) { return r.ok ? r.json() : { available: false, reason: "error" }; })
      .then(function (data) {
        if (!data.available) { renderQuizUnavailable(data, lang); return; }
        renderQuestion(data, lang);
      })
      .catch(function () { renderQuizUnavailable({ reason: "error" }, lang); });
  }

  function renderQuizUnavailable(data, lang) {
    var msg = data.reason === "not_enough_words"
      ? "Mimo needs a few more " + esc(lang.name) + " words before quizzing here."
      : "Mimo couldn't start a quiz for " + esc(lang.name) + " right now.";
    quizBox.innerHTML =
      '<div class="lm-question">🌱 A little more help needed</div>' +
      '<div class="lm-qdef">' + msg + " Every translation and review helps Mimo learn.</div>" +
      '<a class="btn btn-primary" href="/tasks">Help add words</a>';
  }

  function renderQuestion(data, lang) {
    var q = data.question;
    quizBox.innerHTML =
      '<div class="lm-quiz-head"><span class="lm-chips">' + chips() + "</span></div>" +
      '<div class="lm-question">Which one means <span class="lm-qterm">' + esc(q.term) +
        "</span> in " + esc(data.language) +
        (data.dialect ? " · " + esc(data.dialect) : "") + "?</div>" +
      '<div class="lm-qdef">' + esc(q.definition || "") + "</div>" +
      '<div class="lm-options" id="lmOptions"></div>' +
      '<div class="lm-feedback" id="lmFeedback"></div>' +
      '<button type="button" class="btn btn-primary lm-next" id="lmNext" ' +
        'style="display:none;">Next question →</button>' +
      '<p class="small muted" style="margin-top:.6rem;">' +
        (q.verified ? "✓ verified by the community"
                    : "🌱 leading community sample (pending full verification)") +
      "</p>";

    var opts = document.getElementById("lmOptions");
    q.options.forEach(function (text, i) {
      var b = el('<button type="button" class="lm-option">' + esc(text) + "</button>");
      b.addEventListener("click", function () { answerQuestion(b, i, q); });
      opts.appendChild(b);
    });
    document.getElementById("lmNext").addEventListener("click", function () { startQuiz(lang); });
  }

  function answerQuestion(btn, choice, q) {
    var buttons = quizBox.querySelectorAll(".lm-option");
    buttons.forEach(function (b) { b.disabled = true; });
    state.quiz.total += 1;
    var fb = document.getElementById("lmFeedback");
    if (choice === q.answer_index) {
      btn.classList.add("is-correct");
      state.quiz.correct += 1;
      state.quiz.streak += 1;
      fb.innerHTML = '✅ <span style="color:#0b5e3f;">Safi! That\'s right.</span>';
      mimoSay("Hongera! " + q.term + " — you got it! 🎉");
    } else {
      btn.classList.add("is-wrong");
      buttons[q.answer_index].classList.add("is-correct");
      state.quiz.streak = 0;
      fb.innerHTML = "💡 Correct answer: <strong>" + esc(q.options[q.answer_index]) + "</strong>";
      mimoSay('Pole! The right one is "' + q.options[q.answer_index] + '". Now you know it!',
        { mood: "sad" });
    }
    var head = quizBox.querySelector(".lm-chips");
    if (head) head.innerHTML = chips();
    var next = document.getElementById("lmNext");
    if (next) { next.style.display = "inline-block"; next.focus(); }
  }

  // ------------------------------------------------------- chat conversation
  function languageReplies() {
    var withData = state.languages.filter(function (l) { return l.submissions > 0; });
    var langs = (withData.length ? withData : state.languages).slice(0, 6);
    return langs.map(function (lang) {
      return {
        label: lang.name + " · " + lang.submissions,
        onClick: function () {
          addBubble("user", lang.name);
          chooseLanguage(lang);
        }
      };
    });
  }

  function askLanguage() {
    mimoSay("Which language would you like to learn in? 🌍", {
      after: function () { setReplies(languageReplies()); }
    });
  }

  function chooseLanguage(lang) {
    state.selected = lang;
    state.selectedDialect = rememberedDialect(lang);
    highlightPills(lang);
    renderDialects(lang);
    updateSpeakChip();
    mimoSay("Sasa tunaanza " + langLabel(lang) + "! 🎉 I'm learning with " + lang.contributors +
      " friend" + (lang.contributors === 1 ? "" : "s") + " and " + lang.submissions +
      " words so far.");
    state.quiz = { correct: 0, total: 0, streak: 0 };
    loadWord(lang);
    startQuiz(lang);
    sendAwarenessTip(lang);
  }

  function learnReplies(lang) {
    return [
      { label: "Teach me a word", onClick: function () {
          addBubble("user", "Teach me a word"); sendWord(lang); } },
      { label: "Quiz me", onClick: function () {
          addBubble("user", "Quiz me"); playQuiz(lang); } },
      { label: "Another safety tip", onClick: function () {
          addBubble("user", "Another safety tip"); sendAwarenessTip(lang); } },
      { label: "Change language", onClick: function () {
          addBubble("user", "Change language"); askLanguage(); } }
    ];
  }

  function startReplies() {
    return [
      { label: "Teach me a word", onClick: function () {
          addBubble("user", "Teach me a word"); requireLang(sendWord); } },
      { label: "Quiz me", onClick: function () {
          addBubble("user", "Quiz me"); requireLang(playQuiz); } },
      { label: "Safety tip", onClick: function () {
          addBubble("user", "Safety tip"); requireLang(sendAwarenessTip); } },
      { label: "Choose language", onClick: function () { askLanguage(); } }
    ];
  }

  function requireLang(action) {
    if (state.selected) { action(state.selected); return; }
    askLanguage();
  }

  function sendAwarenessTip(lang) {
    fetch("/learn/word?language=" + encodeURIComponent(lang.name) + dialectQuery() + "&category=message")
      .then(function (r) { return r.ok ? r.json() : { available: false }; })
      .then(function (data) {
        if (!data.available) {
          mimoSay("I don't have a safety tip in " + langLabel(lang) + " yet. Help us add one! 🌱");
        } else {
          var w = data.word;
          var text = "🛡️ " + w.translation;
          if (w.term && String(w.term).toLowerCase() !== String(w.translation).toLowerCase()) {
            text += "\n\n(“" + w.term + "”)";
          }
          if (!w.verified) text += "\n🌱 community sample — help us verify it";
          mimoSay(text);
        }
        setReplies(learnReplies(lang));
      })
      .catch(function () {
        mimoSay("Hmm, I couldn't reach my notes just now. Try again in a moment.");
      });
  }

  function sendWord(lang) {
    fetch("/learn/word?language=" + encodeURIComponent(lang.name) + dialectQuery() + "&category=glossary")
      .then(function (r) { return r.ok ? r.json() : { available: false }; })
      .then(function (data) {
        if (!data.available) {
          mimoSay("I don't know a word in " + langLabel(lang) + " yet — will you teach me one? 🌱");
          return;
        }
        var w = data.word;
        var text = "📖 “" + w.term + "” in " + langLabel(lang) + " is “" + w.translation + "”.";
        if (w.definition) text += "\n" + w.definition;
        if (!w.verified) text += "\n🌱 community sample";
        mimoSay(text);
        showWord(w, lang);
      });
  }

  function playQuiz(lang) {
    startQuiz(lang);
    mimoSay("Here comes your question — good luck! 🎯");
    if (quizSection && quizSection.scrollIntoView) {
      quizSection.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function helpReply() {
    mimoSay("I can share a 🛡️ safety tip, 📖 teach you a word, or 🎯 quiz you — " +
      "in any Kenyan language. What would you like?", {
      after: function () { setReplies(startReplies()); }
    });
  }

  function handleUserText(raw) {
    var text = String(raw || "").trim();
    if (!text) return;
    addBubble("user", text);
    setReplies([]);
    var t = text.toLowerCase();

    var lang = findLanguage(t);
    if (lang) { chooseLanguage(lang); return; }
    if (/(quiz|test|game|play|question)/.test(t)) { requireLang(playQuiz); return; }
    if (/(tip|advice|awareness|safe|danger|scam|fraud)/.test(t)) { requireLang(sendAwarenessTip); return; }
    if (/(word|teach|learn|translate|vocab|term)/.test(t)) { requireLang(sendWord); return; }
    if (/(language|change|switch|other)/.test(t)) { askLanguage(); return; }
    if (/(help|what can|options|how do)/.test(t)) { helpReply(); return; }
    if (/(hi|hello|hey|karibu|sasa|habari|jambo|niaje)/.test(t)) {
      mimoSay("Karibu! 😊 " + (state.selected
        ? "Ready to keep learning " + state.selected.name + "?"
        : "Which language shall we learn in?"), {
        after: function () { setReplies(state.selected ? learnReplies(state.selected) : startReplies()); }
      });
      return;
    }
    if (/(thank|asante|thanks)/.test(t)) { mimoSay("Karibu sana! 💜"); return; }

    mimoSay("I'm still learning 😅 — try “teach me a word”, “quiz me”, or tell me your language.");
    setReplies(startReplies());
  }

  // --------------------------------------------------------------- boot
  function introSequence() {
    mimoSay("Karibu! I'm Mimo 🤖 your online-safety buddy.");
    mimoSay("Pick a language, then ask me for a 🛡️ safety tip, 📖 a word, or a 🎯 quiz.");
    askLanguage();
  }

  function boot() {
    scheduleBlink();
    document.addEventListener("mousemove", function (e) {
      trackEyes(e.clientX, e.clientY);
    });
    document.addEventListener("touchmove", function (e) {
      if (e.touches && e.touches[0]) trackEyes(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });

    if (chatForm) {
      chatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        greetOnce();
        var value = chatInput ? chatInput.value : "";
        if (chatInput) chatInput.value = "";
        handleUserText(value);
      });
    }

    applySoundUi();
    if (soundBtn) {
      soundBtn.addEventListener("click", function () { setMuted(!muted); });
    }
    if (playBtn) {
      playBtn.addEventListener("click", function () {
        if (muted) setMuted(false);
        if (currentAudio) { currentAudio.pause(); currentAudio.currentTime = 0; }
        greeted = true;
        playSound("intro");
      });
    }
    var chatEl = document.getElementById("lmChat");
    if (chatEl) {
      chatEl.addEventListener("click", function (e) {
        if (e.target && e.target.closest && e.target.closest(".lm-chat-tools")) return;
        greetOnce();
      });
    }

    fetch(API + "/stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.totals = data.totals;
        state.languages = data.languages || [];
        renderStats(data.totals);
        renderLanguages(state.languages);
        renderLeaders(data.top_contributors);
        renderBars(state.languages.filter(function (l) { return l.submissions > 0; }));
        introSequence();
      })
      .catch(function () {
        if (statsBox) statsBox.innerHTML = '<span class="lm-loading">Mimo could not reach the API.</span>';
        if (langBox) langBox.innerHTML = '<span class="lm-loading">Try refreshing the page.</span>';
        introSequence();
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
