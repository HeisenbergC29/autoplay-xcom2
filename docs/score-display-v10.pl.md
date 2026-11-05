# Licznik punktów nad przyciskiem — v12

Pole nad przyciskiem „Autoplay” pokazuje wynik bieżącej misji i maksimum,
np. `0/46000`. Rozmiar czcionki jest odczytywany z przycisku. Pole odświeża
się co 0,25 s także przy wyłączonym autoplay i pozostaje widoczne po schowaniu
przycisku. Nie przechwytuje kliknięć mapy ani nawigacji klawiaturą.
Dotychczasowe położenie przycisku, statusu i znacznika pozostaje takie samo.

## Korekta premii początkowych

V11 przyznawało z góry 6000 na każdego kwalifikowanego żołnierza. To było
błędne założenie naszego profilu porównawczego: parametry 1000 za brak ran
oraz 5000 za przeżycie potraktowano jak przydział początkowy. Tabele gry
opisywały nimi maksymalną pulę i kary, a zaobserwowany wynik Legacy zaczynał
się od 0. [Raport v11](report-2026-11-03-v11-score.pl.md) potwierdza stare
`~24000` w zwykłym `SabotageCC` oraz natywny start Legacy od zera.

V12 usuwa tę bazę zarówno z HUD-u, jak i domyślnej analizy raportów. Nowy profil
`wotc_legacy_observed_v2` zaczyna od `~0/—` przed zaobserwowanymi zdarzeniami:

- pierwsza rana kwalifikowanego żołnierza: −1000, najwyżej raz;
- potwierdzona strata: −5000, najwyżej raz;
- zabicia, jawne zaliczenia celów i ratunek cywilów: dotychczasowe reguły v2;
- brak przydziału początkowego i brak zakładanych premii końcowych.

Leczenie nie cofa już naliczonej kary. Wykrwawienie i samo HP równe zero nie
potwierdzają śmierci. Wynik może być ujemny.

[Domyślny profil v2](../tools/legacy-score-rules.json) i archiwalny
[profil v1](../tools/legacy-score-rules-v1.json) mają różne bazy. Sum obu wersji
nie porównujemy bez przeliczenia. Historyczne logi v11 nadal zawierają stare
wyświetlone wartości v1; nowy analizator może obliczyć dla nich osobną ocenę v2.

## Wynik gry

Odczyt natywnej punktacji nie jest zmieniany przez v12. W Legacy licznik
pokazuje wkład bieżącej misji: aktualny wynik drabinki minus wynik przeniesiony
na początek tego etapu. F8 nie zeruje licznika, a kolejny etap nie dolicza
ponownie poprzedniej misji. Brak pewnego odczytu stanu początkowego daje „—”.

Maksymalna pula pochodzi z odczytu używanego przez okno punktacji Legacy
i jest zachowywana dla misji. Nie jest wpisana na stałe ani zmniejszana po
zabiciach, ranach czy stratach. W natywnym Challenge Mode używana jest para
wynik/maksimum z funkcji podsumowania gry. Znany wynik bez maksimum pozostaje
widoczny, np. `1200/—` lub `0/—`.

Nie odtwarzamy nieobserwowanych końcowych rozliczeń gry. Ich pełna implementacja
jest natywna; brak dowodu premii na starcie nie oznacza, że gra nigdy nie
stosuje żadnych końcowych premii. HUD pokazuje natywny wynik po aktualizacji gry.

## Częściowa ocena w niepunktowanych misjach

Tylda w `~wartość/—` oznacza ocenę porównawczą moda. Maksimum pozostaje nieznane.
Ocena nie zastępuje liczb Legacy ani Challenge Mode i nie jest oficjalnym wynikiem.

Obserwator działa z HUD-em, również przed F8 i przy wyłączonym autoplay.
Historia jest przeglądana porcjami, więc po wczytaniu wartość może dojść do
aktualnego stanu po kilku odświeżeniach. Historyczna widoczność ogranicza
informacje o wrogach, a zdarzenia celów sprzed utworzenia HUD-u lub wczytania
zapisu mogą być nieobserwowane. Zniknięcie wroga nie oznacza zabicia.
HUD i raport mogą mieć różne okna obserwacji i różne częściowe sumy.

Odczyty nie przyznają punktów grze, nie zmieniają jej stanów ani decyzji planera.
Obserwator usuwa nasłuchy przy usunięciu HUD-u lub zmianie trybu. `hud_score`
zachowuje tekst wyświetlony podczas rejestracji, a nie późniejszy wynik końcowy.

## Kierunek osłony

V12 nie zmienia taktycznej oceny osłon. W walce planer pyta grę o osłonę
od położenia każdego widocznego przeciwnika do rozważanego pola żołnierza.
Osłona od przodu nie zabezpiecza automatycznie flanki. Uwzględniane są także
LOS i zagrożenie wręcz. Bez widocznych przeciwników eksploracja ocenia osłonę
względem celu marszu; nie zna przyszłego kierunku ukrytych wrogów.

## Kompilacja i sprawdzenie

Nowy kod wymaga kompilacji Windows według [instrukcji Legacy](legacy-test.pl.md).
Rejestr uruchomionego autoplaya ma wskazywać `revision=mission-report-v12`.
Testy źródeł i kontraktów SDK nie potwierdzają jeszcze naliczania w prawdziwej grze.

1. Zwykła misja: początek `~0/—`, bez 6000 za żołnierza.
2. Pierwsza rana −1000, ponowne obrażenia bez kolejnej tej samej kary,
   potwierdzona strata −5000, zabicie, jawny cel i ratunek cywila.
3. Legacy: natywny start, zgodna pula, wynik ujemny i stałe maksimum.
4. Kolejny etap i zapis ze środka misji: bez doliczania poprzedniego etapu
   i bez zerowania po wczytaniu lub F8.
5. Widoczność przy OFF i schowanym przycisku, kliknięcia mapy pod licznikiem,
   różne rozdzielczości i skale UI.
6. Usunięcie HUD-u lub zmiana trybu: bez podwójnego naliczania zdarzeń
   i bez pozostawionych nasłuchów.

Do raportu dopisz widoczną wartość i moment odczytu. Korekta licznika nie jest
zmianą taktyki ani dowodem poprawy wyniku misji.
