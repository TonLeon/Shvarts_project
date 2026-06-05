/* Цифровое собрание сочинений Елены Шварц — site JS.
   Two features only; everything else on the site works without JS:
   1. comparison page: version switching + line-diff highlighting
   2. photo gallery lightbox (Материалы)                            */

(function () {
  'use strict';

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ---------- comparison page ---------------------------------- */

  var data = document.getElementById('versions-data');
  if (data) {
    var versions = JSON.parse(data.textContent);

    function metaHtml(v) {
      var rows = [['Год написания', v.written],
                  ['Опубликовано в', v.edition],
                  ['Год публикации', v.published]];
      return rows.filter(function (r) { return r[1]; }).map(function (r) {
        return '<dt>' + r[0] + '</dt><dd>' + esc(r[1]) + '</dd>';
      }).join('');
    }

    function render(side) {
      var v = versions[+document.getElementById('select-' + side).value];
      document.getElementById('head-' + side).textContent = v.head;
      document.getElementById('text-' + side).textContent = v.text;
      document.getElementById('meta-' + side).innerHTML = metaHtml(v);
    }

    ['a', 'b'].forEach(function (side) {
      document.getElementById('select-' + side)
        .addEventListener('change', function () { render(side); });
      render(side);
    });

    document.getElementById('compare').addEventListener('click', function () {
      var a = versions[+document.getElementById('select-a').value].text.split('\n');
      var b = versions[+document.getElementById('select-b').value].text.split('\n');
      var outA = [], outB = [], i = 0, j = 0;

      while (i < a.length && j < b.length) {
        if (!a[i].trim()) { outA.push(esc(a[i])); i++; continue; }
        if (!b[j].trim()) { outB.push(esc(b[j])); j++; continue; }
        if (a[i] !== b[j]) {
          outA.push('<span class="diff diff--a">' + esc(a[i]) + '</span>');
          outB.push('<span class="diff diff--b">' + esc(b[j]) + '</span>');
        } else {
          outA.push(esc(a[i]));
          outB.push(esc(b[j]));
        }
        i++; j++;
      }
      for (; i < a.length; i++) outA.push('<span class="diff diff--a">' + esc(a[i]) + '</span>');
      for (; j < b.length; j++) outB.push('<span class="diff diff--b">' + esc(b[j]) + '</span>');

      document.getElementById('text-a').innerHTML = outA.join('\n');
      document.getElementById('text-b').innerHTML = outB.join('\n');
    });
  }

  /* ---------- catalog: год написания validation ----------------- */

  var filters = document.querySelector('.catalog__filters');
  if (filters) {
    var popup = null;

    function showYearPopup(message) {
      if (!popup) {
        popup = document.createElement('div');
        popup.className = 'popup';
        popup.innerHTML =
          '<div class="popup__card" role="alertdialog" aria-modal="true">' +
          '<p class="popup__text"></p>' +
          '<button type="button" class="button popup__ok">Хорошо</button>' +
          '</div>';
        document.body.appendChild(popup);
        popup.querySelector('.popup__ok').addEventListener('click', function () {
          popup.hidden = true;
        });
        popup.addEventListener('click', function (e) {
          if (e.target === popup) popup.hidden = true;
        });
        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape' && popup) popup.hidden = true;
        });
      }
      popup.querySelector('.popup__text').textContent = message;
      popup.hidden = false;
      popup.querySelector('.popup__ok').focus();
    }

    filters.addEventListener('submit', function (e) {
      var bad = ['year_from', 'year_to'].some(function (name) {
        var input = filters.elements[name];
        if (!input || !input.value) return false;
        var year = parseInt(input.value, 10);
        return isNaN(year) || year < +input.min || year > +input.max;
      });
      if (bad) {
        e.preventDefault();
        var min = filters.elements.year_from.min;
        var max = filters.elements.year_from.max;
        showYearPopup('Елена Шварц писала с ' + min + ' по ' + max +
                      ' год — таких дат в архиве нет. Пожалуйста, поправьте годы поиска.');
      }
    });
  }

  /* ---------- gallery lightbox ---------------------------------- */

  var gallery = document.querySelector('.gallery');
  if (gallery) {
    var links = Array.prototype.slice.call(gallery.querySelectorAll('.gallery__link'));
    var current = -1;

    var box = document.createElement('div');
    box.className = 'lightbox';
    box.hidden = true;
    box.innerHTML =
      '<button class="lightbox__close" aria-label="Закрыть">&times;</button>' +
      '<button class="lightbox__prev" aria-label="Предыдущая">&larr;</button>' +
      '<img class="lightbox__img" alt="Фотография из архива Елены Шварц">' +
      '<button class="lightbox__next" aria-label="Следующая">&rarr;</button>';
    document.body.appendChild(box);
    var img = box.querySelector('.lightbox__img');

    function show(index) {
      current = (index + links.length) % links.length;
      img.src = links[current].href;
      box.hidden = false;
      document.body.style.overflow = 'hidden';
    }

    function close() {
      box.hidden = true;
      document.body.style.overflow = '';
      links[current].focus();
    }

    links.forEach(function (link, index) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        show(index);
      });
    });

    box.querySelector('.lightbox__close').addEventListener('click', close);
    box.querySelector('.lightbox__prev').addEventListener('click', function () { show(current - 1); });
    box.querySelector('.lightbox__next').addEventListener('click', function () { show(current + 1); });
    box.addEventListener('click', function (e) { if (e.target === box || e.target === img) close(); });

    document.addEventListener('keydown', function (e) {
      if (box.hidden) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') show(current - 1);
      if (e.key === 'ArrowRight') show(current + 1);
    });
  }
})();
