# Trzecia próba Legacy Operations — mission-report-v7

Najnowszy `Launch.log` w `AutoplayXCom2-20261102-200526-33bbd2f7.zip` zawiera
sesję `2026-11-2_20-59-12-60_915`, `ChallengeAbductionGasStation`, trudność `2`
(Dowódca), rewizję `mission-report-v7`. Wynik to **loss w turze 3**. Numery linii
poniżej odnoszą się do tego pliku; początek sesji jest w linii 273, wynik w 2665.

## Integralność i zakres

Wszystkie 4 wpisy manifestu są zgodne z rozmiarami i SHA-256 logów. Tylko
`Launch.log` jest nowy: 558763 bajty, SHA-256
`ed6896deef5f54b90215c420bc549b7a88e8248a6252612a4ff91ebd683d7c58`.
Backup `20.57.09` powtarza próbę v6, `20.32.16` — v5, a `17.31.00` — starszego
Gatecrashera. We wszystkich dotychczasowych raportach jest siedem odrębnych
sesji, z czego trzy dotyczą Legacy Operations.

Zapisano 13 zaakceptowanych poleceń bez odrzuceń: 6 ruchów, 4 `StandardShot`,
2 `SniperStandardFire` i jedno `MedikitHeal`. Nie użyto granatu, Aid Protocol,
overwatch ani hunker. Trzech żołnierzy zginęło; Central został niezdolny do
działania z 1 HP (linie 2656–2659). Brak `ScriptWarning`, `Accessed None`,
`Critical` i `Fatal`. Raport dochodzi do wyniku misji.

## Potwierdzone działanie poprawek v7

- Central nie wykonuje wcześniejszej szarży poza wsparcie. W decyzji 3 strzela
  sojusznik (linia 929), a w decyzji 4 Central dobija cel zwykłym strzałem
  (linie 1015, 1130), pozostając przy oddziale.
- Specjalista wycofuje się w decyzji 5 (linia 1154).
- Koszt AP jest uwzględniany: w decyzji 2 snajper ma potencjalną utratę
  ofensywy 18.92, a ruch otrzymuje 4.8122 (linia 826). W decyzji 13 wybiera
  strzał 46.876 przed ruchem 23.3384 (linie 2444–2449).
- Leczenie działa: w decyzji 9 przywraca snajperowi 1 → 5 HP (linie 1842, 1907).
  Późniejsze zabicie go przez dwa Faceless nie oznacza, że leczenie nie zaszło.

## Pozostałe problemy planowania

W decyzjach 6 i 7 ranny snajper zużywa oba AP na odwrót. Ryzyko maleje
133.13 → 64.9251 → 23.4488; snajper ma wtedy 1 HP. Pole
`potential_attack_loss=20.36` przy drugim ruchu nie jest zastosowaną karą:
dotychczasowy wyjątek awaryjny celowo zachowuje priorytet takiego odwrotu.
Nie jest to dowód, że projekcja AP przestała działać.

W decyzji 10 Central wybiera ruch 40.1088 przed strzałem 71%/36.24. Po ruchu
ten sam cel pozostaje legalny, lecz strzał ma 59%/30.96 (linie 1916–2005).
V7 sprawdza pozostałe AP na obecnych celach; nie przewiduje nowej jakości
strzału. Nie należy opisywać tego jako całkowitej utraty LOS lub ataku.
Specjalista po swoim ruchu również nadal ma legalny strzał, a następnie
wybiera dostępne leczenie snajpera.

Najmocniejsza niespójność dotyczy oceny ucieczki przed wręcz: Central oddala
się od Faceless z 4.2426 do 7.6158 pola, a wkład ryzyka maleje z 31.0294 do
17.5369, chociaż przeciwnik nadal może go dosięgnąć. W następnej turze
Faceless faktycznie dociera do Centrala i wyłącza go (linie 2249–2250).
Punktacja przyznaje zatem znaczną ulgę również za ruch wewnątrz osiągalnego
obszaru ataku. Oba miejsca nadal różnią się ryzykiem ostrzału innych wrogów;
sam ten przypadek nie dowodzi, że każdy odwrót był błędem.

Po pudle Centrala sojusznik zadaje Faceless 6 obrażeń, pozostawiając 4 HP
(linia 2147). Regeneracja podnosi je do 6 (linia 2181), a strzał snajpera
w kolejnej turze chybia przy 58% (linia 2520). To dodatkowy koszt ograniczonej
ofensywy, lecz alternatywnego przebiegu silnik nie rozegrał.

## Dlaczego nadal nie było granatu

22 skany dały 271 ocen punktów: 131 odrzuceń zasięgu, 11 widoczności i 129
bezpieczeństwa wybuchu. Żaden punkt nie dotarł do wyceny obrażeń. Najczęstsze
migawki ostatniego powodu to `objective_near_blast` i `dangerous_scenery_in_blast`.
Dotychczasowy log nie identyfikuje konkretnego obiektu ani nie rozróżnia
braku jego geometrii od rzeczywistej bliskości. Nie ma podstaw, by sam brak
granatów uznać za błędny priorytet pojedynczego celu.

Planer już próbuje punktów pomiędzy parami wrogów. V8 dodaje alternatywne
punkty poprzeczne oraz dane o blokującym obiekcie i dostępności jego geometrii.
Nie usuwa ochrony sojuszników, ciał ani celów misji i nie zakłada, że samochód
na pewno eksploduje po trafieniu granatem.

## Granice danych i dalsza próba

Agregat analizatora podaje trzy pudła przyjazne i jedno wrogie dla zdarzeń
`result`. Dodatkowy cel ataku obszarowego ma `result_target.hit=3`
(`eHit_Miss`, linia 2662); agregat nie jest kompletną liczbą wszystkich celów.

Poprawki v8 i rozpatrzone sugestie opisuje
[opis priorytetów, granatów i zagrożeń](tactics-v8.pl.md).
Kompilacja Windows i wynik v8 w grze pozostają do sprawdzenia. Testy źródeł
nie dowodzą zwycięstwa ani tego, że tę porażkę można przypisać jednej decyzji.
