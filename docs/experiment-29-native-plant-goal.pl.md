# Eksperyment #29 — rzeczywista kotwica interakcji PlantBomb

Baza v25: `eae4db165f679d6cac56d6e207900106c4ed3f55`.
Integracja v26 uwzględnia PR #51 z atakami na potwierdzony przekaźnik.
Windows WOTC SDK i gra tego wariantu: **NOT RUN**. Końcowy SHA do
kompilacji wskazuje LEAD w issue #4.

## Problem

[Raport v25](report-2026-11-12-v25.pl.md) ma 75 obserwacji AA_NoTargets
oraz 39 AA_CannotAfford_ActionPoints dla Interact_PlantBomb, zero AA_Success
i zero wykonanych interakcji. Dawny cel był glintem albo środkiem markera.
Bliskość markera nie dowodzi istnienia prawdziwego punktu interakcji.

## Odczyt rzeczywistego celu

Nowy APX_PlantInteractionKnowledge rozpoznaje istniejący, aktywny
InteractiveObject i zgodnego wizualizera o
InteractionAbilityTemplateName=Interact_PlantBomb. Wymaga posiadanej
zdolności, zgodnego ObjectID, poprawnego stanu oraz CanInteractNormally
(z uwzględnieniem wyposażenia, limitu użyć, aktora i locków). W zwykłym
trybie wiedzy obiekt musi być widoczny; pełne rozpoznanie pozwala
odkryć ten cel z danych mapy.

Actor.InteractPoints jest tylko punktem startu odkrywania. Każde pole
zapytania musi odzyskać właściwy aktor przez natywne
GetInteractionPoints(tilecenter,8,90); sprawdzane są granice obiektu
na Point.Location, tak jak w stock UnitInteractions. Nie przesuwamy
żywego UnitState w historii do symulowanego miejsca.

Dla dużego Berserkera reader pobiera faktyczną footprint przez
GetVisibilityForLocation. Odwraca jej przesunięcia, aby znaleźć możliwe
kotwice przyszłej pozycji; przyszła footprint musi zawierać potwierdzone
pole zapytania. Socket może być na innym poziomie niż stojący żołnierz:
sprawdzane są poziomy Z0,−1,+1,−2,+2 względem pola socketu, każdy osobno
przez natywne zapytanie. Kotwica pochodzi z poziomu potwierdzonego query,
nie z samego poziomu socketu. To zachowuje stockową tolerancję wysokości90
bez wymyślania zgody silnika.

Zgodna geometria wymaga następnie rzeczywistej ścieżki dla tej jednostki.
Wybrana kotwica jest celem podróży, nie obietnicą wykonania interakcji
po jednym ruchu. Dotychczasowy planer wybiera bezpieczny prefiks trasy,
sprawdza pełne hazardy, wsparcie i ekspozycję. Dopiero po rzeczywistym
ruchu ponownie zbudowany native cache może udostępnić PlantBomb.

## Limity i fallback

Jedno FindGoal bada do128 stanów obiektów,32 wpisów cached points,
32 natywnych zapytań świata,64 potencjalne kotwice i4 pełne próby A*.
Wyjścia mają jawne przyczyny: brak aktora, niedostępny stan/interakcja,
brak cached/live punktów, niezgodna footprint, brak ścieżki albo limit.
Native plant approach zapisuje liczby i przyczynę, a ewentualny marker
ma source=mission_marker_unverified:reason. Nie jest certyfikatem interakcji.

Cztery najbliższe próby A* mogą pominąć dalszą osiągalną kotwicę. To
ograniczone wyszukiwanie, nie dowód niemożliwości scenariusza. Wyczerpanie
budżetu albo nieznana geometria nie nadają nowej zdolności czy celu.

Zachowano wymóg co najmniej1 AP dla natywnego PlantBomb, choć interakcja
nie zużywa AP. Specjalny rush nadal wymaga co najmniej2 AP. Ostatni AP
zachowuje ocenę utraconego ataku i ryzyka; nie przywrócono wyjątku #43.
Zmieniono cel podejścia, nie reguły AP, RNG ani natywną punktację.

## Ukończenie i Sweep

Fazę określa dokładny natywny MissionObjective o nazwie PlantBomb.
Tylko bCompleted potwierdza przejście do Sweep. Odległość1,5 pola od
markera, pusty zbiór celów i zużyty interaktor nie oznaczają sukcesu.
Wyczerpany właściwy interaktor może zablokować powrót do niepotwierdzonego
markera, ale nie ustanawia fazy Sweep. Po potwierdzonym PlantBomb planer
korzysta z dotychczasowego ścigania znanych wrogów i pomija stary marker.

## Próba

Po kompilacji końcowego SHA odtworzyć tę samą Blood Killer. Zestawić
Native plant approach, source trasy, faktyczne endpointy i odświeżone
AvailableActions. Sprawdzić prawdziwy AA_Success oraz wykonany PlantBomb,
a następnie Sweep. W razie fallbacku zachować jego przyczynę i liczniki;
nie zwiększać w ciemno premii marszu.

Testy wykonują matematykę offsets/poziomów i sprawdzają kontrakty źródeł
SDK; nie są kompilacją UnrealScript ani potwierdzeniem zwycięstwa.
Kryterium pozostaje: wymagane cele, native win i znany końcowy wynik >0.
Surowe SDK i raporty są prywatne.

## Poprawka po pierwszej kompilacji v26 — 12 XI 2026

Przekazany tylko LEAD plik mod-make.log zawiera **1 unique error /8 warnings**.
Kompilację AutoplayXCom2 przerywa `Unparsed class 'XComWorldData' found while
validating DependsOn entries for 'APX_MissionPlanner'`. Ostrzeżenia dotyczą
źródeł/zasobów SDK/DLC, a nie są przyczyną tego przerwania. Log nie zapisuje
dokładnego SHA lokalnej kopii źródeł.

Dodanie PlantGoalResult do lokalnych zmiennych MissionPlanner wymagało
DependsOn(APX_PlantInteractionKnowledge). To odtwarza znany problem granicy
kompilacji, wcześniej usunięty dla AmbushPreparation w `b87db36`. Poprawka
przywraca listę zależności planera sprzed PR #52, pozostawia strukturę
wewnątrz klasy wiedzy i wystawia TTile/string oraz status int: 1 oznacza
znaleziony cel, −1 zużyty interaktor bez celu, 0 zwykły fallback. Znaleziony
cel nadal ma pierwszeństwo, jeżeli inny interaktor jest zużyty. Cała procedura
odkrywania geometrii i jej limity pozostają identyczne.

Rewizja rejestratora pozostaje v26. Test regresyjny sprawdza brak nowej
zależności i struktury w planerze oraz zachowanie wyjść/priorytetu statusów.
Ponowna kompilacja Windows i gra poprawki pozostają **NOT RUN** do otrzymania
nowych dowodów. Aktualny końcowy SHA do pobrania wskazuje #4.
