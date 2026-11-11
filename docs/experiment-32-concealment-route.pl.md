# Eksperyment #32 — ocenianie ryzyka utraty ukrycia podczas marszu

Baza main v22: `75a83365dc9f862080dc3e8bab22399c1f875a29`.
Wariant runtime: `mission-report-v23`. Weryfikacja w grze jeszcze nie została
wykonana. To osobna zmiana od zasadzek na kolejne grupy (#31) i ofensywnego
AoE (#38).

## Problem

Pełne rozpoznanie przeciwników nie pozwala zachować concealment samo z siebie.
Ukryty żołnierz mógł przekroczyć wykrywalne pole cywila/obcego, dotrzeć do
urządzenia z DetectionRange lub przejść przez niszczoną szybę. Dawna ochrona
istniała tylko podczas przygotowania pierwszej zasadzki i ruchu po loot; zwykły
`ChooseMove` i eksploracja nie korzystały z niej.

## Zmiana

`APX_ConcealmentPlanner` szacuje ryzyko na **całej proponowanej trasie**, bez
modyfikacji stanu gry. Korzysta z natywnego `GetPathPointsFromPath`, widocznych
detektorów (w tym cywilów), `UnitBreaksConcealment`, natywnego LOS i promienia
wykrycia. Przy `EnableFullIntel=true` dołącza aktualne znane pozycje wrogów.
Urządzenia po zhakowaniu nie są traktowane jako aktywne detektory, a żołnierze
z `AbilityRetainsConcealmentVsInteractives` mają właściwy wyjątek.
Zgodnie ze stock `OnUnitEnteredTile`, tryb Challenge nie karze destrukcyjnego
traversalu za samo zniszczenie otoczenia; nadal może zadziałać zwykłe wykrycie.

Normalny `ChooseMove` sprawdza preferowaną trasę do celu. Jeśli trasa zdradza
ukrycie i zadanie nie jest pilne, szuka bezpiecznego niebieskiego alternatywnego
kroku. Oryginalną legalną trasę zatrzymuje jako **fallback**, jeśli nie znajdzie
bezpiecznej — nie zamienia ryzyka w nieskończony stan oczekiwania.
Jeśli nie udało się wyznaczyć prefiksu do dokładnego celu, zachowuje również
najlepszy konstruktywny lokalny ruch sprzed kary za utratę ukrycia. Ten ruch
nadal musi przejść wszystkie kontrole AP, ryzyka, hazardów, wsparcia i kosztu
utraconego ataku. Kara za concealment sama nie powoduje globalnego NoPlan/OFF.
Przy alternatywach nakłada miękką, konfigurowalną karę; ratunek, ewakuacja,
deadline i specjalny sabotaż Blood Killer mają wyższy priorytet. Sama widoczność
wroga przez ukryty oddział nie wyłącza kontroli — może to być niezaangażowany pod.

`APX_ExplorationPlanner` stosuje tę samą miękką ocenę na proponowanych
ścieżkach. `APX_SquadPlanner.PreparationPathIsSafe` używa wspólnego estymatora
dla ukrytych jednostek, przy zachowaniu dotychczasowych kontroli hazardów,
geometrii i wsparcia. Po utracie concealment nie blokuje ruchu wyłącznie z
powodu szyby czy działającego detektora. Przy full intel uwzględnia znane pola
zamiast bezwarunkowo żądać natywnej widoczności każdego pola.

## Koszt i ograniczenia

Domyślne limity jednej inspekcji: 48 pól/trasa, do 96 widocznych/znanych
detektorów oraz 128 nowych natywnych zapytań LOS
(`MaxNativeLOSChecksPerInspection`, twardy zakres 1–512). Tani filtr odległości
poprzedza LOS. Kontroler inicjuje jeden budżet sześciu inspekcji na całą
decyzję, wspólny dla wszystkich jednostek, prefiksu i lokalnego ruchu,
eksploracji, łupu oraz przygotowania zasadzki. To domyślnie najwyżej 768
nowych zapytań LOS tej oceny na decyzję; nie jest to limit istniejących
zapytań innych plannerów. Nie ma dodatkowego resetu per jednostka ani
podwójnego starego skanu detektorów w przygotowaniu.

Niepełna inspekcja zwraca `*_sample_limit`, `native_los_budget` albo
`decision_budget`: nie jest pewnością wykrycia ani bezpieczeństwa. Nieznana
trasa dostaje tę samą skończoną karę co oszacowane ryzyko, bez premii za brak
sprawdzenia. Opcjonalne przygotowanie zasadzki wymaga sprawdzonej trasy;
zwykły marsz zachowuje legalny fallback.

Log `Concealment inspection` podaje jednostkę, długość, oszacowanie i przyczynę
tylko dla faktycznych inspekcji, maksymalnie sześciu w decyzji. To kandydaci,
nie dowód wykonania ruchu. Początek APXREC zawiera ustawioną karę i limit LOS.
Wariant może wymagać profilowania w grze; żadna ocena nie gwarantuje stealth.
Rzeczywista ścieżka, koszty AP, status ukrycia i interakcje nadal należą do
silnika.

## Próba A/B po przeglądzie LEAD

Porównać na tym samym zapisie bazę v22 i wariant v23:

1. Ukryty żołnierz i widoczny cywil/wróg: preferuje legalną ścieżkę bez
   ujawnienia, jeśli istnieje; nie blokuje postępu, jeśli nie ma alternatywy.
2. Wykrywające urządzenie, zhakowane urządzenie, jednostka z Infiltration:
   zachowanie zgodne z aktywnym detektorem i natywnymi wyjątkami.
3. Zniszczenie szyby: zwykła misja kontra Challenge; nie zakładać, że
   wszystkie dźwięki natychmiast ujawniają oddział.
4. Pilna ewakuacja/leczenie/PlantBomb, trucizna, aktywny przeciwnik: dalsze
   wykonywanie akcji przez native AA_Success i ścieżki; brak wiszących
   decyzji i rozkazów mimo wyłączonego autoplaya.
5. GasStation i Blood Killer: każdorazowo zanotować cel, wynik natywny
   i **punkty misji** (finalne, częściowe albo nieznane), zawieszenie,
   użycie grup i utratę concealment.

Ta zmiana nie jest naprawą potwierdzonego zawieszenia Blood Killer v22.
Obserwacyjne śledzenie długiego oczekiwania jest osobnym zadaniem #40;
właściwy obiekt i pole PlantBomb pozostają w #29. Nie trzeba odtwarzać
zawieszenia, aby sprawdzić sam cywil/detektor/szybę w innej misji.

Testy Python i czytanie prywatnych definicji SDK nie są potwierdzeniem
kompilacji WOTC ani wygrania misji. LEAD weryfikuje i scala; użytkownik
kompiluje oraz testuje w grze.
