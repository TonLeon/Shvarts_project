// Сравнение стихотворений в comparison.html
// (Поиск и фильтры на странице «Произведения» теперь работают без JS —
// обычной GET-формой; см. titles.html.)

$('#mySelect_1').change(function(){
                var value = $(this).val()
                $("div#first_poem").empty()
                $("div#first_poem").append(value);
                var meta = $(this).find('option:selected').attr('meta')
                $("div#first_meta").empty()
                $("div#first_meta").append(meta)

              });

$('#mySelect_2').change(function(){
                var value = $(this).val()
                $("div#second_poem").empty()
                $("div#second_poem").append(value);
                var meta = $(this).find('option:selected').attr('meta')
                $("div#second_meta").empty()
                $("div#second_meta").append(meta)

              });

// Возврат на предыдущую страницу
function goBack() {
  window.history.back();
}

// Сравнение стихотворений с выделением разночтений
$(function() {
  $('button#compare').bind('click', function() {
highlight($("pre#new"), $("pre#old"));
function highlight(second_poemElem, first_poemElem){
  var first = 0;
  var second = 0;
  var first_text = '';
  var second_text = '';
  var oldText = first_poemElem.text().split('\n');
  var newText = second_poemElem.text().split('\n');

  while (first < oldText.length && second < newText.length) {

  if (oldText[first].length === 0) {
    first_text += oldText[first] + '\n';
    first = first + 1;
   }
   else if (newText[second].length === 0) {
    second_text += newText[second] + '\n';
    second = second + 1;
   }
   else if (oldText[first] !== newText[second]) {
    first_text += "<span class='highlight_old'>"+ oldText[first] +"</span>\n";
          second_text += "<span class='highlight_new'>"+ newText[second] +"</span>\n";
    first = first + 1;
    second = second + 1;
   }
   else {
    first_text += oldText[first] + '\n';
    second_text += newText[second] + '\n';
    first = first + 1;
    second = second + 1;
   }}


  for (var i = first; i < oldText.length; i++) {
   if (oldText[i] !== newText[second]) {
    first_text += "<span class='highlight_old'>"+ oldText[i] +"</span>\n";
   } else {
    first_text += oldText[i] + '\n';
   }
  }

  for (var i = second; i < newText.length; i++) {
   if (oldText[first] !== newText[i]) {
    second_text += "<span class='highlight_new'>"+ newText[i] +"</span>\n";
   } else {
    second_text  += newText[i] + '\n';
   }
  }

  first_poemElem.html(first_text);
  second_poemElem.html(second_text);
};
})});
