# Czwarty raport Gatecrashera

Archiwum `AutoplayXCom2-20261102-152831-1fa0fb57.zip` zawiera nową sesję
`2026-11-2_16-22-52-641_888` oraz trzy starsze kopie logów. Najnowsza sesja to
`mission-report-v4`, `SabotageCC`, poziom 3 (Legenda), wynik `loss`. Sumy i skróty
SHA-256 wszystkich plików odpowiadają manifestowi archiwum.

## Potwierdzone wyniki

- 27 przyjętych poleceń: 12 ruchów, 10 overwatch, 3 zwykłe strzały, jeden granat
  i jedno przyczajenie. Osiem overwatch przypadało na marsz przed kontaktem.
- Zasadzka zadziałała: w decyzji 18 żołnierz 427 przeszedł do `(23,32)`, w 19
  włączył overwatch, a w 20 strzelec 421 otworzył atak strzałem 66%.
  Otwarcie chybiło. Jedyny zapisany strzał reakcyjny trafił sektoida przy 65%,
  zadając 4 obrażenia, z 10 do 6 HP. Liczba poleceń overwatch nie jest liczbą strzałów.
- Dwaj żołnierze z tyłu mieli jeszcze po dwa AP, ale nie mogli wesprzeć otwarcia
  z aktualnych pozycji. Dystanse do strzelca wynosiły 13 oraz około 11,05 pola.
  Planer dopuszczał tylko ruch, którego koniec już zapewniał linię ostrzału.
  Ich późniejsze ruchy nastąpiły po ujawnieniu. Zapisana propozycja `(19,33)`
  zmniejszałaby oba dystanse do około 6,08 pola, lecz pełną trasę musi dopuścić
  kontrola ukrycia i wykrycia silnika.
- Kolejny zwykły strzał 45% chybił. Pierwsza tura przeciwnika po otwarciu
  zabiła 421 strzałem 75% i 415 strzałem krytycznym 65%. Zmiana pozycji wroga
  zmienia kąty ostrzału; niska ocena ryzyka w obecnej geometrii nie gwarantuje
  bezpiecznej następnej tury.
- W decyzji 25 granat 427 otrzymał ocenę 55,5, wobec jego strzału 50% ocenionego
  na 42,67. Trafił pojedynczego troopera 903 za 3 obrażenia: 4 → 1 HP.
  Brak zarejestrowanych obrażeń sojuszników lub celu misji od tego wybuchu.
  Granat został dopuszczony przez nowy wyjątek dużych obrażeń, bez gwarancji zabicia.
- Po wybuchu jednostka 409 straciła legalny cel: `StandardShot` zmieniło stan
  na `AA_NoTargets`. Następne przyczajenie nie dowodzi pominięcia dostępnego
  dobicia. Cel 903 zginął później od jej strzału 48%.
- Końcowy zapis potwierdza dwa zgony, jednego wykrwawiającego się żołnierza
  i zmianę 409 z `friendly` na `visible_enemy` przy 4 HP. To nie są cztery
  zarejestrowane zgony. Kontrola umysłu jest możliwym wyjaśnieniem zmiany
  przynależności; brak osobnego potwierdzonego wpisu tej zdolności w raporcie.

## Zmiany w `mission-report-v5`

1. Przed ujawnieniem tył oddziału może wykonać bezpieczny ruch doganiający,
   nawet gdy nie uzyska jeszcze linii ostrzału. Wymagane są dwa AP, dostępny
   overwatch z pozostawionym kosztem, dystans ponad limit wsparcia, poprawa
   o co najmniej dwa pola i brak wzrostu ryzyka. Zachowano pełne kontrole trasy,
   wykrycia, widoczności, zagrożeń oraz limit sześciu przygotowań. Dla danego
   żołnierza osiągalna bezpieczna linia ostrzału ma pierwszeństwo.
2. Wybrany granat ma własny podgląd celów, HP, tarcz, obrażeń i punktu lądowania.
   Dotychczas `target=0` i zerowe obrażenia głównego celu wynikały z kontraktu
   granatu; nie opisywały trafianych jednostek. Podsumowanie skanu mogło dotyczyć
   późniejszego odrzuconego punktu. Nowe wpisy oddzielają te dane.
3. Wybrane ruchy zapisują dla widocznych wrogów geometryczną osłonę oraz LOS
   przed ruchem i na docelowym polu, w tym widoczność z domyślnego pola strzelca.
   To pozwoli ocenić dalsze zmiany osłon na podstawie danych zamiast samej
   zagregowanej oceny ryzyka. Kierunek argumentów `GetCoverTypeForTarget`
   potwierdzono w SDK. Zapytanie `CanSeeTileToTile` nie wypełnia `TargetCover`,
   co SDK stwierdza wprost; jego domyślna wartość nie może służyć do oceny osłony.

Ocena osłony nadal nie przewiduje przyszłego ruchu przeciwnika. Na podstawie
tego raportu nie potwierdzono konkretnego błędu zapytania geometrycznego, który
wyjaśniałby śmiertelne trafienia po przemieszczeniu się wrogów.

Testy wykonują rzeczywiste funkcje liczbowe UnrealScript oraz sprawdzają granice
widoczności i interfejsy dostępne w źródłach SDK. Nie zastępują kompilatora ani gry.
Nowe źródła wymagają zbudowania i kolejnej próby. Nie ma jeszcze potwierdzenia
zwycięstwa na Commanderze lub Legendzie. Osobny zapis sprzed pierwszego kontaktu
pozwoliłby porównać kolejne wersje na tej samej mapie i ustawieniu oddziału.
