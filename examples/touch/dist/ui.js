/* Lune Touch reference binder — scope titles + heat-source type panels. */
(function () {
  'use strict';
  function q(sel) { return document.querySelector(sel); }
  function qa(sel) { return document.querySelectorAll(sel); }
  function syncScope() {
    var r = q('input[name="scope"]:checked');
    if (!r) return;
    var title = r.getAttribute('data-title') || '';
    var sub = r.getAttribute('data-sub') || '';
    qa('[data-bind="scope.title"]').forEach(function (el) { el.textContent = title; });
    qa('[data-bind="scope.sub"]').forEach(function (el) { el.textContent = sub; });
  }
  function syncHs() {
    var r = q('input[name="hs_type"]:checked');
    var t = (r && r.value) || q('[data-hs-type]') && q('[data-hs-type]').getAttribute('data-hs-type') || 'http';
    qa('[data-hs-type]').forEach(function (el) { el.setAttribute('data-hs-type', t); });
  }
  document.addEventListener('change', function (e) {
    if (!e.target || !e.target.name) return;
    if (e.target.name === 'scope') syncScope();
    if (e.target.name === 'hs_type') syncHs();
  });
  syncScope();
  syncHs();
})();
