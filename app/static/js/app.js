// Copy the selected language's dialects into the dialect dropdown on demand.
document.addEventListener("change", function (event) {
  if (event.target && event.target.matches("[data-language-select]")) {
    var form = event.target.closest("form");
    if (!form) return;
    var target = form.querySelector("[data-dialect-select]");
    if (!target) return;
    var languageId = event.target.value;
    target.innerHTML = '<option value="0">Loading…</option>';
    fetch("/api/v1/languages")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var lang = (data.languages || []).find(function (l) { return String(l.id) === String(languageId); });
        var options = ['<option value="0">— None / community-wide —</option>'];
        if (lang) {
          lang.dialects.forEach(function (d) {
            options.push('<option value="' + d.id + '">' + d.name + '</option>');
          });
        }
        target.innerHTML = options.join("");
      })
      .catch(function () {
        target.innerHTML = '<option value="0">— None / community-wide —</option>';
      });
  }
});
