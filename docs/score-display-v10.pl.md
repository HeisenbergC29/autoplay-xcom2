# Licznik punktów nad przyciskiem — v10 / v11

Pole nad przyciskiem „Autoplay” pokazuje wynik bieżącej misji i maksimum,
np. `0/46000`. Rozmiar czcionki jest odczytywany z przycisku. Pole odświeża
się co 0,25 s także przy wyłączonym autoplay i pozostaje widoczne po schowaniu
przycisku. Nie przechwytuje kliknięć mapy ani nawigacji klawiaturą.
Dotychczasowe położenie przycisku, statusu i znacznika pozostaje takie samo.

## Wynik gry

W Legacy licznik pokazuje wkład **bieżącej misji**: aktualny wynik drabinki
minus wynik przeniesiony do taktycznego stanu początkowego tego etapu.
Nie zeruje się przy F8 i nie dolicza poprzednich misji po przejściu do
następnego etapu. Brak pewnego odczytu stanu początkowego daje „—”.

Maksymalna pula pochodzi z natywnego odczytu używanego przez okno punktacji
Legacy i jest zachowywana dla tej misji. Nie jest wpisana na stałe ani
zmniejszana po zabiciach, ranach czy śmierciach. W natywnym Challenge Mode
wyświetlana jest para wynik/maksimum z funkcji używanych przez podsumowanie gry.
Od v11 znany wynik pozostaje widoczny bez maksimum, np. `1200/—` lub `0/—`.

Wynik może być ujemny. W [próbie v9](report-2026-11-03-legacy-v9.pl.md)
gra rozpoczęła od 0 i zakończyła obserwowany okres na −10000 przy puli 46000.
Odpowiadałoby to `-10000/46000`, bez ograniczania do zera. Ewentualne późniejsze
premie pojawią się dopiero wtedy, gdy gra zaktualizuje wynik.

## Ocena porównawcza w niepunktowanych misjach

[Raport v10 z SabotageCC](report-2026-11-03-v10-sabotage.pl.md) nie zawierał
natywnej punktacji. Wtedy HUD pokazywał „—”, a osobny analizator mógł wyliczyć
częściową ocenę 5200. Po nowym wyborze użytkownika v11 udostępnia ocenę
porównawczą również na HUD-zie takich misji, np. `~5200/—`.

Tylda oznacza częściową ocenę moda według profilu
`wotc_legacy_observed_v1` z [reguł raportów](../tools/legacy-score-rules.json).
Maksimum pozostaje nieznane. Ta ocena nie zastępuje natywnych liczb Legacy
ani Challenge Mode i nie jest oficjalnym wynikiem gry.

Profil zaczyna od premii 6000 za każdego obserwowanego kwalifikowanego
żołnierza: 1000 za brak ran i 5000 za przeżycie. Czterech takich żołnierzy
daje początkowo `~24000/—`. To przewidziane premie porównawcze, które można
utracić, a nie zdobyte punkty gry. Pierwsza rana odbiera 1000 najwyżej raz;
leczenie nie zwraca tej premii. Potwierdzona śmierć odbiera 5000 najwyżej raz.
Wykrwawianie i samo HP równe zero nie potwierdzają śmierci.

Do oceny dochodzą zaobserwowane potwierdzone zabicia, jawne zaliczenia celów
i uratowani cywile. Stosowane są te same reguły typów i spadku punktów z turami
co w analizatorze. Wynik może rosnąć i maleć. Obserwator działa z HUD-em,
również przed F8 i przy wyłączonym autoplay.

Ocena zawsze pozostaje częściowa: historyczna widoczność ogranicza informacje
o przeciwnikach, a zdarzenia celów sprzed utworzenia HUD-u lub wczytania zapisu
mogą być nieobserwowane. Przegląd historii odbywa się porcjami, więc po wczytaniu
wartość może dojść do aktualnego stanu po kilku odświeżeniach. Zniknięcie wroga
z widoku nie oznacza zabicia. Nie uzupełniamy braków fikcyjnymi zdarzeniami;
HUD i raport mogą mieć różne okna obserwacji oraz różne częściowe sumy.

Odczyty nie przyznają punktów, nie zmieniają stanów gry ani decyzji planera.
Obserwator porównawczy usuwa swoje nasłuchy przy usunięciu HUD-u lub zmianie
trybu; stan misji i wyłączenie autoplaya pozostają rozdzielone.

## Kierunek osłony

V11 nie zmienia taktycznej oceny osłon. W walce planer pyta grę o osłonę
od położenia **każdego widocznego przeciwnika** do rozważanego pola żołnierza.
Osłona od przodu nie zabezpiecza automatycznie flanki. Uwzględniane są także
LOS i zagrożenie wręcz. Bez widocznych przeciwników eksploracja ocenia osłonę
względem celu marszu; nie zna przyszłego kierunku ukrytych wrogów.
[Telemetria tej oceny](report-2026-11-03-v10-sabotage.pl.md).

## Kompilacja i sprawdzenie

Nowy kod wymaga kompilacji Windows według [instrukcji Legacy](legacy-test.pl.md).
Rejestr uruchomionego autoplaya ma wskazywać `revision=mission-report-v11`.
Testy źródeł i kontraktów SDK nie potwierdzają jeszcze wyglądu ani naliczania
nowego licznika w prawdziwej grze.

Sprawdź:

1. Początek Legacy: licznik przed F8, poprawna pula, zgodna wielkość czcionki.
2. Zmianę wyniku po zabiciu i pierwszej ranie oraz wynik ujemny.
3. Stałe maksimum po zabiciach i stratach; znany wynik bez maksimum jako `1200/—`.
4. Kolejny etap i zapis ze środka misji: bez doliczania poprzedniego etapu
   i bez zerowania po wczytaniu lub przełączeniu autoplaya.
5. Widoczność przy OFF i schowanym przycisku, kliknięcia mapy pod licznikiem,
   różne rozdzielczości i skalę UI.
6. Zwykłą misję: `~wartość/—`, początkowe premie, jednorazową karę za ranę,
   potwierdzone zgony i zabicia, cele poboczne i ratunek cywilów.
7. Wczytanie zapisu, przejście do następnej misji i usunięcie HUD-u: bez
   podwójnego naliczania zdarzeń albo pozostawionych nasłuchów.

Do raportu dopisz widoczne wartości i moment odczytu. Najnowsza próba v10
zakończyła się porażką; zmiana licznika nie jest dowodem poprawy taktyki v11.
