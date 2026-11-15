# Poprawka kompilacji v43 — #99

Pierwszy log Windows WOTC MakeCommandlet dla przekazanej paczki źródeł
`119187162a3fe8e663f990839a81a952295b0b56` kończy się **FAILURE: 1 error / 1 warning**.
Log nie zapisuje SHA; przypisanie do tej paczki wynika z przekazania użytkownika
i zgodności pliku/linii. Surowy log i ścieżki hosta pozostają prywatne.
HELPER tego pliku nie otrzymał; poprawkę wykonuje LEAD.

## Przyczyna i zmiana

- `APX_MissionPlanner.uc:2596`: `Right type is incompatible with '&&'`.
  Przy konwersji warunku na flagę int wyrażenie `A && B ? 1 : 0`
  wymaga jawnego grupowania całego warunku. Stock kompilator odrzucił
  niepogrupowaną postać. Dodano nawiasy w zgłoszonym miejscu oraz dwóch
  analogicznych przypisaniach końcowych flag zwykłej trasy i pierwszego blue.
  Poszczególne warunki, ich kolejność oraz wartości 1/0 pozostają te same.
- `APX_PatrolAmbushPlanner.uc:215`: parametr `CanWaitWindow.bExpired`
  kolidował z polem klasy. Parametr nazywa się teraz `bWindowExpired`;
  wywołanie nadal przekazuje pole `bExpired` i zachowuje warunek oczekiwania.

To poprawka składni i nazwy, bez zmiany zamierzonej taktyki, AP, punktacji
lub konfiguracji SDK. Marker pozostaje **mission-report-v43**; nową paczkę
identyfikuje dokładny SHA w [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
Nie trzeba ponownie zmieniać TLE/Day0 ani budować pakietów bazowych.

## Weryfikacja

- **882 prywatne testy PASS / 0 SKIP** z udostępnionymi SDK/configami.
- Audyt referencji SDK: **30 klas moda / 31 skonfigurowanych nazw PASS**.
- 20 testów polityk i kontraktów marszu/zasadzki PASS; nowy preflight ma
  6 testów PASS. Uruchomiony na oryginalnym blobie `1191871` wykrywa dokładnie
  trzy miejsca: 2596, 2876 i 2877; poprawione źródła nie mają tych naruszeń.
- Niezależny przegląd zmian źródłowych i pozostałych ternary w modzie.
  Końcowy review SHA, wynik CI i zweryfikowany ZIP zapisuje LEAD w #99/#4.
  Żaden z tych testów nie uruchamia Windows WOTC MakeCommandlet.

Nowa kontrola źródeł odrzuca niepogrupowany warunek logiczny przy `? :`,
w tym trzy pierwotne postacie błędu; pomija komentarze i literały oraz
akceptuje poprawnie pogrupowane warunki. To wąska kontrola konkretnej
klasy defektów, nie kompilator UnrealScript.

Poprzednie zielone testy Python i audyt referencji nie wykryły błędu składni
stock kompilatora. **Windows make poprawionej paczki oraz gra v43: NOT RUN**.
Ponowna kompilacja użytkownika jest konieczna przed próbą misji. Dotychczasowe
scenariusze i kryterium autonomous WIN + known final mission score >0 zachowane.
