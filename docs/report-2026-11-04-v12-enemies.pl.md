# Próba v12 — przeciwnicy i podstawy dalszej oceny zagrożeń

Raport `AutoplayXCom2-20261103-231358-fb9325a4.zip` zawiera cztery sesje.
Najnowsza to `2026-11-4_0-5-12-178_889`: **v12**, `SabotageCC`, trudność 3,
**porażka w turze 8**. Pozostałe sesje powtarzają wcześniejsze próby v10/v11.
Wszystkie cztery pliki zgadzają się z rozmiarem i SHA-256 manifestu.

## Wynik i zakres obserwacji

`Logs/Launch.log`: start w linii 660, zakończenie w linii 7072,
`outcome=loss`, `history_pending=0`. Przyjęto wszystkie **40 rozkazów**:
16 ruchów, dziewięć `StandardShot`, dziewięć `HunkerDown`, trzy overwatch
i trzy przeładowania. Nie wybrano granatu. Potwierdzono sześć zabitych
widocznych przeciwników.

Na końcu trzech żołnierzy (`415`, `421`, `427`) nie żyje. `409` ma 1 HP,
pozostaje żywy, ale wykrwawia się i jest obezwładniony. Nie zaliczamy go
jako czwartej potwierdzonej śmierci. Brak `ScriptWarning`, `Accessed None`,
`Fatal` i `Critical` w najnowszym logu nie zastępuje audytu kompilatora.

Pierwszy zapis HUD-u (linia 880) wskazuje `~0` i profil
`wotc_legacy_observed_v2`. Potwierdza to usunięcie premii początkowych.
Ostatni zaobserwowany tekst wynosi −12200 (linia 6819); analiza wszystkich
zarejestrowanych zdarzeń daje częściowy subtotal **−17200**. Ostatnia śmierć
następuje później, więc nie są to odczyty z tego samego momentu. Natywnej
punktacji tej zwykłej misji nie zarejestrowano. Znak „—” w logu ma postać
U+0014; nie ma obrazu HUD-u, aby ocenić jego wygląd na ekranie.

## Przeciwnicy ujawnieni w tej próbie

| Szablon | Pierwsze widoczne HP / maksimum | Potwierdzone użyte zdolności |
| --- | --- | --- |
| `AdvTrooperM1` | 4 / 4 | `StandardShot` |
| `AdvCaptainM1` | 7 / 7 | `MarkTarget` |
| `Sectoid` | 10 / 10 | `StandardShot`, `Mindspin` |
| `PsiZombie` | 8 / 8 | `StandardMelee` |

W logu rozpoznano 13 widocznych wrogich `StandardShot`, jedno `MarkTarget`,
jedno `Mindspin` i jedno `StandardMelee`. Liczby opisują zarejestrowane
rozstrzygnięcia, nie pełny repertuar wroga. `ammo=-1` przy przeciwnikach jest
redakcją obserwatora: raport nie podaje faktycznej amunicji ani szablonu broni.
Wyposażenie i pozostałe zdolności wymagają sprawdzenia definicji gry.

## Sekwencje istotne dla doboru taktyki

- Oficer `907` oznaczył `427` przez `MarkTarget` (linia 3837, tura 3).
  Zaraz potem strzał troopera `910` obniżył jego HP z 4 do 1 (linia 3849).
  Sam ten przebieg nie dowodzi, czy bez oznaczenia strzał by chybił; uzasadnia
  sprawdzenie mechaniki oznaczenia i oceny zagrożenia wspierającego.
- Sektoid `915` trafił `415` strzałem z 4 do 1 HP (linia 4725), a później
  użył `Mindspin` na `409` (linia 6236). W tej fazie własna jednostka ma
  `panicked=True`, `mind_controlled=False` (linie 6181 i 6311). Nie należy
  utożsamiać sukcesu `Mindspin` z udanym przejęciem kontroli umysłu.
- Zombie `1759` zakończył próbę trafieniem `StandardMelee` w `421`
  (linia 7071). We wcześniejszych ocenach ma `melee_threat_reach=-1`
  (np. linia 5808), więc planer stosował oszacowanie zastępcze.
- Przygotowanie zasadzki w decyzjach 2 i 4 podniosło przewidywane ryzyko
  końcowego pola z 24,78 do 55,65 oraz z 44,22 do 80,97 (linie 987 i 1158).
  Ruchy następowały podczas koordynacji ukrytego otwarcia. Warto sprawdzić,
  czy przygotowanie pozostawia rozsądną osłonę po rozpoczęciu walki;
  nie jest to dowód, że przed ujawnieniem wróg mógł już oddać strzał.

Żaden kandydat ataku nie ma dodatnich `known_released_allies` lub
`known_linked_enemies`. Ten raport nie potwierdza działania premii za zabicie
źródła aktywnej więzi. Brak kandydata strzału w sektoida w późnych decyzjach
nie rozstrzyga jego legalnej dostępności: zapis wybranego kandydata nie jest
pełną listą wszystkich celów. Sam brak wyboru nie dowodzi błędu priorytetu.

## Zakres dotychczasowych kontaktów

Po usunięciu duplikatów sesji we wszystkich dostępnych katalogach
`report-*` zidentyfikowano **17 sesji** i dziesięć szablonów występujących
jako widoczni przeciwnicy:

`AdvCaptainM1`, `AdvPriestM3`, `AdvTrooperM1`, `BerserkerMP`, `Faceless`,
`PsiZombie`, `PsiZombieHuman`, `Sectoid`, `Soldier` i `Viper`.

`Soldier` obejmuje przejętego członka oddziału. Nazwa `BerserkerMP` pochodzi
z szablonu i nie stanowi dowodu rozegrania multiplayera. Ta lista kontaktów
nie jest katalogiem całej gry; konfiguracja nowo załadowanej mapy ani
startowa tabela punktacji nie potwierdza jeszcze zauważenia danej jednostki.

Dalsza wiedza o zdolnościach, wyposażeniu, bazowych statystykach i ich
kontrach powinna pochodzić z SDK oraz zainstalowanych szablonów, z osobnym
oznaczeniem danych konfiguracyjnych, których nie ma w otrzymanych źródłach.
[Zasady raportowania i ograniczenia obserwacji](mission-recording.pl.md).
