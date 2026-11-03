# Priorytety celów, granaty i zagrożenie wręcz — v8

Zmiany wynikają z [raportu v7](report-2026-11-02-legacy-v7.pl.md) i sugestii
użytkownika. Dotyczą wspólnej logiki autoplaya dla misji WOTC i oficjalnych DLC.
V8 wymaga zbudowania na Windows i kolejnej próby w grze.

## Kiedy atakować źródło kontroli

SDK potwierdza, że usunięcie odpowiedniego efektu kontroli przy śmierci źródła
przywraca poprzedniego właściciela jednostki. Psi zombie ma aktywną więź do
twórcy; jego zdolność `KillSiredZombies` usuwa powiązane zombie po śmierci
źródła. Nie każda nowa jednostka na mapie podlega takim zasadom.

V8 rozpoznaje rzeczywiste aktywne efekty i referencje źródła na widocznych
przeciwnikach. Dla kontroli członka oddziału sprawdza wyłącznie jego dawnego
właściciela sprzed efektu, tak jak kod SDK; nie czyta dawnej pozycji. Nie nadaje
premii na podstawie samej nazwy `Sectoid` ani pozycji ukrytych jednostek.

Do oceny możliwego dobicia źródła dochodzi premia za znane skutki: odzyskanie
sojusznika gracza lub usunięcie powiązanych widocznych zombie. Premia jest
ograniczona i skalowana szansą zabicia źródła wyliczoną z legalnego strzału,
podglądu obrażeń, pancerza i tarcz. Przy zerowej szansie dobicia wynosi zero.
Wielostrzałowy atak zachowuje korektę niezależnych rzutów. Ataki obejmujące
dodatkowe cele nie dostają tej premii, aby nie liczyć skutków dwukrotnie.

W praktyce pewne zabicie kontrolera może wygrać z nieco łatwiejszym zabiciem
jednego zombie. Słaby strzał do pełnozdrowego źródła nadal może przegrać
z pewnym usunięciem bliskiego zagrożenia. Planer nie zabrania legalnego ataku
na zombie ani przejętą jednostkę w sytuacji awaryjnej. Odzyskany przez śmierć
źródła sojusznik nie dostaje w tej ocenie obietnicy dodatkowego strzału:
SDK zeruje stary budżet AP, a nowy przyznaje warunkowo, gdy trwa tura
przywróconego właściciela. Następna decyzja korzysta z faktycznej dostępności.

To ocena pojedynczej dostępnej akcji. Nie jest jeszcze planem kilku strzałów
do pełnozdrowego kontrolera ani pełnym przeszukiwaniem kolejności całej tury.

## Najgroźniejszy, najsłabszy czy najłatwiejszy do trafienia

Dotychczasowa ocena już łączy szansę trafienia, spodziewane obrażenia,
prawdopodobieństwo dobicia, rany i ograniczenie nadmiarowych obrażeń.
Wartość usunięcia broni przeciwnika jest przybliżona jego ofensywą. V8 dodaje
konkretne skutki zabicia źródła. Każdy cel jest przeliczany po faktycznym
wyniku poprzedniego rozkazu, więc pudło nie rezerwuje optymistycznie zabicia.

Stała reguła „zawsze najsłabszy” albo „zawsze największa szansa trafienia”
pomijałaby wpływ celu na resztę walki. Obecna ocena nadal jest heurystyką;
nie przewiduje wszystkich umiejętności wrogów ani ich przyszłych decyzji.

## Granat między wrogami i obok przeszkody

Planer już sprawdza pozycje wrogów, środki każdej pary i punkty przy krawędzi
zasięgu rzutu. V8 dodaje dwa punkty przesunięte poprzecznie względem pary,
wewnątrz wspólnego obszaru promienia. Mogą objąć obu wrogów i ominąć
chronionego sojusznika lub obiekt znajdujący się przy środku pary.

Wszystkie pule dzielą dotychczasowy ograniczony budżet. Punkt jest jedynie
propozycją: silnik sprawdza podłogę, trajektorię, miejsce lądowania, rzeczywiste
cele i promień. Nadal obowiązują kontrole sojuszników, cywilów, odzyskiwalnych
ciał, celów misji i niebezpiecznej scenerii.

## Samochody i reakcje łańcuchowe

Pomysł ma wartość taktyczną, ale obecny podgląd SDK po zniszczeniu obiektu
nie potwierdza, czy konkretny granat zniszczy go teraz, tylko uszkodzi lub
zapali, ani jakie dalsze obiekty uruchomią kolejne efekty. Potrzebny jest
model progów zniszczenia, zdarzeń i wszystkich wtórnych obszarów obrażeń.
V8 nie dodaje automatycznego celowania w samochody jako źródła dodatkowych
obrażeń i zachowuje dotychczasowe blokowanie niezamodelowanej propagacji.

Rozszerzono za to diagnostykę blokowania. Rozdziela rzeczywisty radial damage,
powiązane obiekty i ogólną flagę niszczenia otoczenia. Ta ostatnia jest
domyślnie włączona w SDK i może obejmować zwykłe fragmenty konstrukcji;
nie należy utożsamiać jej automatycznie z samochodem wybuchającym natychmiast.
Nowe dane pozwolą sprawdzić konkretne blokady bez usuwania zabezpieczeń na ślepo.

## Odwrót wciąż w zasięgu wręcz

Zamiast przyznawać dużą ulgę za każde oddalenie od Faceless, rozpoznane style
wręcz wyznaczają możliwy obszar ruchu i ataku następnej tury. Model używa
mobilności, standardowego budżetu tury oraz natywnej geometrii zdolności;
nie odczytuje bieżących, ukrytych AP przeciwnika.

Wewnątrz tego obszaru pozostaje wysoka podstawa ryzyka, niezależna od osłony.
Nieznane style zachowują poprzednie przybliżenie. Obszar nie jest legalną
przyszłą trasą: ściany i decyzje przeciwnika mogą sprawić, że model przeceni
zagrożenie. Wyjście poza niego również nie stanowi gwarancji bezpieczeństwa.

Ocena zachowanej ofensywy po ruchu nadal sprawdza przede wszystkim AP.
Nie wylicza dokładnej nowej szansy trafienia z docelowego pola.

## Dane do następnej próby

- `revision=mission-report-v8` potwierdza uruchomienie nowej kompilacji.
- `known_released_allies` i `known_linked_enemies` przy ataku opisują znane
  skutki śmierci celu, a nie gwarantowany wynik ani dodatkowe AP.
- `melee_threat_reach` w podglądzie ruchu podaje rozpoznany zasięg w polach;
  `-1` oznacza brak obsługi danego modelu i poprzednią heurystykę.
- `pair_offset_centers` liczy włączone do budżetu alternatywy dla pary.
- `blast_blocker_kind/id/class/geometry` rozróżnia obiekt, brak interfejsu,
  pustą geometrię i rzeczywistą bliskość. ID, klasa i szczegóły scenerii są
  ujawniane tylko dla własnych lub aktualnie widocznych obiektów.
- `blast_blocker_radial/children/surrounding` i `blast_safe_radius_units`
  opisują ostatni odrzucony kandydat, nie pełny histogram skanu ani punkt
  faktycznie wybranego rzutu. Ukryte jednostki pozostają zredagowane.

Weryfikacja źródeł: 218 testów Python bez pominięć, audyt odwołań do SDK
oraz trzy zestawy PowerShell zaliczone. Kompilacja Windows i wynik v8 w grze
pozostają do potwierdzenia.

[Instrukcja kompilacji i próby](legacy-test.pl.md).
