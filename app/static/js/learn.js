/* Mimo — the learners interface. Talks to the public API. */
(function () {
  "use strict";

  var API = "/api/v1";
  var bot = document.getElementById("lmBot");
  var speech = document.getElementById("lmSpeech");
  var langBox = document.getElementById("lmLanguages");
  var statsBox = document.getElementById("lmStats");
  var wordBox = document.getElementById("lmWord");
  var leadersBox = document.getElementById("lmLeaders");
  var barsBox = document.getElementById("lmBars");
  var quizBox = document.getElementById("lmQuiz");

  var state = { totals: null, languages: [], selected: null,
    quiz: { correct: 0, total: 0, streak: 0 } };
  var talkTimer = null;
  var happyTimer = null;
  var sadTimer = null;

  // ---------------------------------------------------------------- Mimo
  function mimoSay(text, opts) {
    opts = opts || {};
    if (!speech) return;
    speech.textContent = text;
    if (bot) {
      bot.classList.add("is-talking");
      bot.classList.remove("is-happy");
      clearTimeout(talkTimer);
      talkTimer = setTimeout(function () {
        bot.classList.remove("is-talking");
        if (opts.happy !== false) {
          bot.classList.add("is-happy");
          clearTimeout(happyTimer);
          happyTimer = setTimeout(function () { bot.classList.remove("is-happy"); }, 2200);
        }
      }, Math.min(2600, 420 + text.length * 28));
    }
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
      pill.addEventListener("click", function () { selectLanguage(lang, pill); });
      langBox.appendChild(pill);
    });
    if (langBox.firstElementChild) {
      var first = langBox.firstElementChild;
      selectLanguage(
        (withData.length ? withData : languages)[0],
        first
      );
    }
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

  function selectLanguage(lang, pill) {
    state.selected = lang;
    document.querySelectorAll(".lm-pill").forEach(function (p) {
      p.classList.toggle("is-active", p === pill);
    });
    mimoSay("Sasa tunaanza " + lang.name + "! I'm learning " + lang.name +
      " with " + lang.contributors + " friend" + (lang.contributors === 1 ? "" : "s") +
      " and " + lang.submissions + " words so far.");
    loadWord(lang);
    state.quiz = { correct: 0, total: 0, streak: 0 };
    startQuiz(lang);
  }

  function loadWord(lang) {
    if (!wordBox) return;
    wordBox.innerHTML = '<p class="lm-loading">Mimo is fetching a ' + esc(lang.name) + " word…</p>";
    fetch(API + "/translations/phishing?language=" + encodeURIComponent(lang.name))
      .then(function (r) { return r.ok ? r.json() : { translations: [] }; })
      .then(function (data) {
        if (data.translations && data.translations.length) {
          var t = data.translations[Math.floor(Math.random() * data.translations.length)];
          showWord(t, true);
          return;
        }
        // no verified word yet — show a lively invitation instead
        return fetch(API + "/translations?language=" + encodeURIComponent(lang.name))
          .then(function (r) { return r.ok ? r.json() : { translations: [] }; })
          .then(function (d2) {
            if (d2.translations && d2.translations.length) {
              showWord(d2.translations[0], true);
            } else {
              wordBox.innerHTML =
                '<div class="lm-word"><span class="lm-term">' + esc(lang.name) + "</span>" +
                '<div class="lm-trans">Be the first to teach Mimo a word! 🌱</div>' +
                '<div class="lm-def">No verified translation yet — ' + lang.submissions +
                " community samples are waiting for review.</div>" +
                '<a class="lm-badge" href="/tasks/phishing">Help verify one →</a></div>';
              mimoSay("I don't know this word in " + lang.name +
                " yet. Will you teach me?");
            }
          });
      })
      .catch(function () {
        wordBox.innerHTML = '<p class="lm-loading">Mimo had trouble reaching the word. Try another language?</p>';
      });
  }

  function showWord(t, verified) {
    wordBox.innerHTML =
      '<div class="lm-word">' +
        '<span class="lm-term">' + esc(t.term_name || t.term) + " · " + esc(t.language) +
        (t.dialect ? " (" + esc(t.dialect) + ")" : "") + "</span>" +
        '<div class="lm-trans">' + esc(t.translation) + "</div>" +
        '<div class="lm-def">' + esc(t.definition || t.context || "A cybersecurity word to know.") + "</div>" +
        '<span class="lm-badge">' + (verified ? "✓ community verified" : "✓ verified") + "</span>" +
      "</div>";
    mimoSay("Here's a word we can trust in " + t.language + ": “" + t.translation +
      "”. Pretty cool, right?");
  }

  // ---------------------------------------------------------------- quiz
  function chips() {
    return '<span class="lm-chip">⭐ Score ' + state.quiz.correct + "/" + state.quiz.total + "</span>" +
      '<span class="lm-chip">🔥 Streak ' + state.quiz.streak + "</span>" +
      (state.selected ? '<span class="lm-chip">🌍 ' + esc(state.selected.name) + "</span>" : "");
  }

  function startQuiz(lang) {
    if (!quizBox) return;
    quizBox.innerHTML = '<p class="lm-loading">Mimo is thinking of a question…</p>';
    fetch("/learn/quiz?language=" + encodeURIComponent(lang.name))
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
        "</span> in " + esc(data.language) + "?</div>" +
      '<div class="lm-qdef">' + esc(q.definition) + "</div>" +
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
        { happy: false });
      mimoFeel("sad");
    }
    var head = quizBox.querySelector(".lm-chips");
    if (head) head.innerHTML = chips();
    var next = document.getElementById("lmNext");
    if (next) { next.style.display = "inline-block"; next.focus(); }
  }

  // --------------------------------------------------------------- boot
  function boot() {
    scheduleBlink();
    document.addEventListener("mousemove", function (e) {
      trackEyes(e.clientX, e.clientY);
    });
    document.addEventListener("touchmove", function (e) {
      if (e.touches && e.touches[0]) trackEyes(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });

    mimoSay("Karibu! I'm Mimo. Let me show you what our community has built…");

    fetch(API + "/stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.totals = data.totals;
        state.languages = data.languages || [];
        renderStats(data.totals);
        renderLanguages(state.languages);
        renderLeaders(data.top_contributors);
        renderBars(state.languages.filter(function (l) { return l.submissions > 0; }));
        var t = data.totals;
        mimoSay("Wow! " + t.languages_with_data + " language communities have shared " +
          t.submissions.toLocaleString() + " words and " + t.assessments +
          " peer reviews. Pick a language to dive in!");
      })
      .catch(function () {
        if (statsBox) statsBox.innerHTML = '<span class="lm-loading">Mimo could not reach the API.</span>';
        if (langBox) langBox.innerHTML = '<span class="lm-loading">Try refreshing the page.</span>';
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
