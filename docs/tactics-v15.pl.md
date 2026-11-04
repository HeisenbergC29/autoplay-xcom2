# V15: wykorzystanie AP, ruch i chmury trucizny

Nowy cel próby to **ukończyć misję zwycięstwem z wynikiem większym od zera**.
Samo zwycięstwo przy wyniku ujemnym lub równym zero nie zalicza próby.
Oficjalny rezultat gry pozostaje zapisany osobno od tej oceny projektu.
[Raport, który poprzedza te zmiany](report-2026-11-04-v14-poison.pl.md).

## Ruch przed strzałem

Zmiana pozycji może poprawić atak, jeżeli po ruchu zostają odpowiednie AP
i korzyść nie wymaga nadmiernego odsłonięcia żołnierza. V15 dodaje ograniczoną
ocenę niebieskiego ruchu z zachowaniem legalnego podstawowego strzału.
Nie podnosi ogólnie wartości każdego ruchu ani nie zakłada, że każde podejście
jest lepsze od ataku z obecnego pola.

Punktem wyjścia jest aktualny legalny `StandardShot` lub `PistolStandardShot`
do widocznego wroga. Natywny podgląd widoczności z rozważanego pola i warunki pojedynczego celu
sprawdzają możliwość celowania. Projekcja szansy jest
ograniczoną heurystyką zmiany znanych modyfikatorów zasięgu i osłony;
**nie jest pełnym natywnym podglądem przyszłego trafienia**.
Nie zmienia pozycji jednostki w historii, by symulować podgląd.

Wariant wymaga pozostawienia kosztu ataku, znanej i bezpiecznej trasy,
wsparcia oraz kontroli ekspozycji. Zakres jest ograniczony do podstawowych
strzałów i odpowiednich flag natywnego celowania. Nie prognozuje dowolnych
umiejętności, nowo odkrytych celów ani ruchu na inny poziom wysokości.
Wyłączony jest przy ukryciu, rozpoznanych zdolnościach zależnych od pozostania
w miejscu i widocznych reakcjach władców. Po rzeczywistym ruchu kontroler
ponownie odczytuje legalne akcje oraz natywną szansę trafienia.

Mała poprawa dobrego strzału nie wystarcza do kosztownego przestawiania.
Podobnie strzał snajpera wymagający dwóch AP nie staje się dostępny po ruchu
tylko dlatego, że inne podstawowe strzały kosztują jeden AP.

## Inne kombinacje czynności

Koszt akcji zależy od zdolności, sprzętu i typów punktów. Dwa punkty nie
oznaczają zawsze „ruch i atak”, a zdolność bez zużycia AP może nadal wymagać
posiadania określonego punktu. Kontroler po każdej wykonanej akcji ponownie
sprawdza dostępność następnej; nie wysyła niezweryfikowanej kolejki rozkazów.

Ocena kombinacji musi zachować natywne koszty i warunki. Nie wolno zakładać
darmowego przeładowania, dodatkowej amunicji, gotowego cooldownu ani kolejnego
strzału wyłącznie na podstawie nazwy zdolności. Dodatkowa ocena obejmuje obecnie Aid Protocol lub leczenie przed zachowanym,
aktualnie legalnym atakiem. Projekcja AP działa na lokalnej kopii punktów
z kontrolą ich typów i kosztów; nie zmienia stanu jednostki. Nie planuje
przeładowania z hipotetyczną amunicją: po prawdziwym przeładowaniu kontroler
zwykle odczytuje akcje ponownie. Nie jest to planer dowolnej sekwencji całej
tury. Scenariusze nadal obejmują ruch z zachowaniem interakcji i różne typy AP.

## Trucizna na mapie i na żołnierzu

`APX_HazardKnowledge` rozpoznaje chmurę trucizny na własnym bieżącym polu
lub polu obecnie widocznym dla oddziału. Sprawdza aktualną robotyczność
i odporność na Poison. Istniejącego `Poisoned` nie uznaje za odporność.
Natywna kontrola pozostałych zagrożeń nadal działa na zwykłych trasach.

Osobny ruch wyjścia z chmury wymaga czystego, widocznego końca trasy.
Dopuszcza ciągły początek drogi przez chmurę, z której żołnierz wychodzi;
nie pozwala tym wyjątkiem przechodzić przez ogień lub kwas ani ponownie
wejść w chmurę po dotarciu do czystego pola. Nadal sprawdza niebieski koszt
trasy, wsparcie i oceniane zagrożenie. Ratunek, cel misji i wartościowy atak
pozostają kandydatami w ocenie działań.

Wyjście ogranicza dalszy kontakt i odświeżanie efektu. **Nie usuwa już
nałożonego zatrucia ani jego kolejnych obrażeń.** Status jednostki oraz chmurę
na mapie trzeba oceniać osobno; sam spadek HP w logu nie określa ich źródła.

## Ocena końca misji

Analizator dodaje `attempt_verdict`, zachowując oficjalne `outcome`.

| Wynik gry | Pewny wynik misji | Ocena próby |
| --- | --- | --- |
| zwycięstwo | większy od zera | zaliczona |
| zwycięstwo | zero lub wynik ujemny | niezaliczona |
| porażka | dowolny lub nieznany | niezaliczona |
| zwycięstwo lub brak końca | brak pewnej końcowej punktacji | niepotwierdzona |

Natywne punkty bieżącej misji mają pierwszeństwo. V15 zapisuje
`mission_points`, `mission_points_known` i `mission_final` w `game_score`.
W Legacy wynik jest odnoszony do rzeczywistego startu etapu, bez doliczania
wcześniejszych misji i bez traktowania F8 jako początku punktacji.
Końcowy znacznik dotyczy zaobserwowanego, zatwierdzonego zakończenia po
nadrobieniu historii. Nie gwarantuje nagród, których gra jeszcze nie zapisała.

Surowy `cumulative_score`, delta od włączenia rejestratora i ostatni odczyt
HUD-u nie zastępują końcowych punktów misji. W misjach bez punktacji gry
można użyć kompletnej oceny porównawczej v2; częściowe `~wartość/—` nie
potwierdza zaliczenia. Reguły `wotc_legacy_observed_v2` nadal zaczynają od
zera i nie otrzymują nowych premii za samo zwycięstwo.

## Następna próba

Zbuduj źródła v15 na Windows i zainstaluj świeży `dist\AutoplayXCom2.zip`.
Sprawdź `revision=mission-report-v15`. Kompilacja i pełna próba v15 w grze
pozostają niepotwierdzone do otrzymania odpowiednich wyników.

Porównaj słaby strzał przy dwóch AP z dostępnym bezpiecznym przestawieniem,
dobry strzał z małą poprawą, brak AP po ruchu, dwupunktowy strzał snajpera,
wsparcie przed atakiem oraz ucieczkę z wielopolowej chmury. Sprawdź również
odporność, trwający status po wyjściu, ponowne wejście, ogień/kwas na trasie
i sytuację bez bezpiecznej drogi. Zachowaj ekran końca misji oraz raport ZIP.
[Instrukcja próby](legacy-test.pl.md) · [Lista testów](TESTING.pl.md) ·
[Rejestracja](mission-recording.pl.md).
