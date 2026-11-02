# AI przeciwników jako baza i przygotowanie zasadzki

Tak, mechanizm drzewa zachowań może uruchamiać rozkazy także dla jednostki
gracza. W dostarczonym SDK potwierdzają to `XComGameState_Unit.AutoRunBehaviorTree`
i `XGAIBehavior.StartRunBehaviorTree`. Samo uruchomienie drzewa nie zapewnia
jednak poprawnej taktyki oddziału XCOM.

`XGAIBehavior.GetAllKnownEnemyStates` korzysta z danych wiedzy AI, a przy ich
braku pobiera `GetPlayableUnits` przeciwnego gracza. To może udostępnić pełną
listę przeciwników zamiast kontaktów widocznych dla człowieka. Ocena ruchu ma
też zależności od gracza AI, grupy i jego pamięci podręcznej. Bezpośrednie
przejęcie tych ścieżek wymagałoby osobnej adaptacji widoczności, sterowania,
kończenia tur i zatrzymywania autoplaya.

Mod już korzysta z natywnych reguł dostępności akcji, trasowania, widoczności,
podglądu trafienia i obrażeń oraz trajektorii granatu. Własny planer wybiera
rozkazy z tych danych. Z AI przeciwników można przenosić sposób oceny osłon,
zagrożeń i współpracy, sprawdzając każdą zależność. Nowa koordynacja korzysta
między innymi z natywnego sprawdzania zarezerwowanych AP, tak jak mechanizmy
oceniające gotowość sojuszników do overwatch. Nie dodaje zależności od Highlandera.

## Zakres dodany w `mission-report-v4`

Przed wybranym atakiem ofensywnym planer sprawdza ukrycie drużynowe wszystkich
żywych, nieobezwładnionych żołnierzy lokalnego gracza. Wymaga co najmniej dwóch.
Indywidualne ukrycie jednego Reapera po ujawnieniu reszty nie uruchamia tej reguły.

- Wybrany strzelec otwierający jest pomijany podczas przygotowań i zachowuje AP.
- Pozostali mogą wykonać niebieski ruch do linii ostrzału, jeśli mają co najmniej
  dwa standardowe AP, dostępny overwatch i zapas AP na jego koszt.
- Ruch wymaga natywnej ścieżki, obecnie widocznych pól, wsparcia oddziału,
  braku zagrożeń oraz kontroli stref wykrycia widocznych jednostek i urządzeń.
  Odrzucane są trasy wybijające okna, otwierające drzwi kopnięciem lub niszczące
  ściany. Przygotowanie nie ustanawia pierwszej pozycji na wyższym dachu.
- Żołnierz z przydatnym strzałem lub linią ostrzału może włączyć dostępny
  wariant overwatch. Brak takiej linii nie powoduje ślepego overwatch w tym planerze.
- Po każdym rozkazie sytuacja jest oceniana ponownie. Domyślnie najwyżej sześć
  rozkazów w turze służy przygotowaniu. Gdy brak kolejnego dopuszczonego
  przygotowania albo kończy się budżet, pierwotne planowanie może wykonać atak.

Nie jest to plan wielu tur. Nie przewiduje nieznanej trasy patrolu, ruchu wroga
po ujawnieniu ani pewnego trafienia z reakcji. Ukryte jednostki nie służą do
wyznaczania stref wykrycia; mogą nadal spowodować nieoczekiwane ujawnienie.
Natywna kompilacja i zachowanie w grze pozostają do potwierdzenia.

## Poprawka po logu kompilacji `b891b9d`

Próba na Windows zatrzymała się przed analizą funkcji: `Unparsed class
'X2GameRuleset' found while validating DependsOn entries for 'APX_Controller'`.
Nowe połączenie kontrolera z typem struktury planera wymagało dodatkowego
`DependsOn`. Poprawka przywraca wcześniejszą listę zależności kontrolera,
a strukturę przygotowania pozostawia wewnątrz planera. Kontroler otrzymuje
jednostkę, akcję, indeks celu, ścieżkę i ocenę przez zwykłe parametry wyjściowe.
Pusta ścieżka oznacza overwatch, a ścieżka z co najmniej dwoma polami — ruch.
Reguły wyboru przygotowania pozostają takie same.

Log zawiera jeden błąd i osiem ostrzeżeń bibliotek SDK. Ostrzeżenia nie są
przyczyną przerwania tej próby. Po pobraniu poprawionych źródeł ponów budowanie
na zachowanym SDK bez `-BuildBase`, jeśli baza jest już gotowa. Przenośne testy
i przegląd interfejsów przechodzą; poprawka wymaga ponownej kompilacji Windows.

## Granaty i pozostałe granice

Pojedynczy cel nie musi już zawsze mieć mniej HP niż minimalne obrażenia
granatu. Nowy wyjątek wymaga przewagi co najmniej 12 punktów oceny nad najlepszym
dostępnym zwykłym strzałem tej samej jednostki, po odjęciu kosztu zasobu.
Wymaga także minimalnych obrażeń równych co najmniej 75% HP i maksymalnych
wystarczających do zabicia albo dostępnego strzału sojusznika z co najmniej 50%
szansą trafienia i minimalnymi obrażeniami wystarczającymi na pozostałe HP.
Nie zakłada z góry zniszczenia osłony. Pancerz i tarcze są uwzględniane.
Kontrole legalności, trajektorii i bezpieczeństwa wybuchu nadal obowiązują.

Ta zmiana realizuje ograniczoną wersję zasadzki wymienionej wcześniej w granicach
README. Osobne planery broni ciężkiej i efektów trwałych, zarządzanie zasobami
na kolejne etapy oraz pełne przechodzenie nietypowych misji DLC pozostają
otwartymi zadaniami. Rozszerzanie ich wymaga konkretnych scenariuszy i raportów.

## Ustawienia i kontrola

```ini
[AutoplayXCom2.APX_Controller]
CoordinateConcealedAmbush=true

[AutoplayXCom2.APX_SquadPlanner]
MaxCandidateTiles=64
MaxPreparationActionsPerTurn=6
```

`CoordinateConcealedAmbush=false` wyłącza ten etap. Limit przygotowań równy zero
również go pomija. Testy numeryczne obejmują sytuację pierwszego strzału z raportu,
zachowanie akcji strzelca otwierającego, koszt ruchu i overwatch, granice stref
wykrycia oraz porównanie granatu ze słabym i dobrym strzałem. Kontrole źródeł
SDK potwierdzają obecność używanych interfejsów; nie zastępują kompilacji.

W raporcie `ambush_setup` podaje jednostkę przygotowującą się i aktualnego
strzelca otwierającego. Faktyczne przyjęcie rozkazu potwierdza dopiero `chosen`.
`ambush_opening` oznacza brak kolejnego przygotowania w danej decyzji;
sam znacznik nie dowodzi trafienia ani udanej zasadzki.
