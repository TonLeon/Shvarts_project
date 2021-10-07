// Поиск на странице titles.html


$(function() {
  $('button#process_input').bind('click', function() {
    $.getJSON('/background_process', {
      search: $('input[name="search"]').val(),
      }, function(data) {
              $("div#result").empty();
              var element = document.getElementById("time_period");
              element.innerHTML = "Результаты поиска:"; 
              if (data.result.length !== 0){
              $(data.result).each(function (index, value) { console.log(value)
                $("div#result").append('<pre class="search_result"><a class="titles__poem" href="../' + value[4] +
                      value[0] + '/">' + 
                    value[1]+ '</a>'+ '<p class="bibliography">Год написания: '+ value[3] + 
                    '</p><p class="bibliography">Опубликовано в: '+ value[2] + '</p></pre>');
          });
        }
              else{
                $("div#result").append('<pre>По Вашему запросу ничего не обнаружено. Попробуйте еще раз.</pre>')
              };
        });
        return false;
        });
      });

// Выдача стихотворений 60-х по годам на titles.html

$(function() {
  $('a#sixties').bind('click', function() {
    $.getJSON('/filter_poems_by_period', function(data) {
      $("div#result").empty();
      var element = document.getElementById("time_period");
      element.innerHTML = "Стихотворения 1960-х годов";
      var result = data.result
      let year = result[0][2]
      $(data.result).each(function (index, value) {
        if(index > 0){
          if (value[2] === year){
        $("div#result").append('<pre><a class="titles__poem" href="../texts_60_' + value[0]+ '/">' + value[1] + '</a></pre>');
      }
          else{
            year = value[2]
            $("div#result").append('<h3 class="year">'+ value[2] +'</h3><pre><a class="titles__poem" href="../texts_60_' + value[0]+ '/">' + value[1] + '</a></pre>');
          };
  }
        else{$("div#result").append('<h3 class="year">'+ year +'</h3><pre><a class="titles__poem" href="../texts_60_' + value[0]+ '/">' + value[1] + '</a></pre>');
    }})
  })
})});
    // $.getJSON('/background_process', {console.log(1)})

//Выдача стихотворений 70-x
    $(function() {
      $('a#seventies').bind('click', function() {
          $("div#result").empty();
          var element = document.getElementById("time_period");
          element.innerHTML = "Стихотворения 1970-х годов"; 
        }
     
    )})

// Сравнение стихотворений в comparison.html

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