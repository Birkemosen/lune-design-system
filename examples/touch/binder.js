/* Lune Touch referencebinder — varmekildens type styrer, hvad Varme-arket viser (.hs-type-*). */
(function () {
  'use strict';
  function syncHs() {
    var r = document.querySelector('input[name="hs_type"]:checked');
    if (!r) return;
    document.querySelectorAll('[data-hs-type]').forEach(function (el) { el.setAttribute('data-hs-type', r.value); });
  }
  document.addEventListener('change', function (e) { if (e.target && e.target.name === 'hs_type') syncHs(); });
  syncHs();
})();
