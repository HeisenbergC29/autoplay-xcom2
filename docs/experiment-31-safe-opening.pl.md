# Eksperyment #31a — osłonięte otwarcie walki i kontrola ryzyka tras

Baza `64c28e76b035bcda92a0ecc902f38ed5c889f88e` (v23).
Wariant integracji `mission-report-v24`. PR #43 pozostaje poza integracją,
ponieważ proponowany tryb ostatniego AP omijał wcześniejsze kontrole ryzyka
i utraconego ataku. Zachowujemy obecne zabezpieczenia v21–v23. Windows SDK
compile / test w grze tego wariantu jeszcze **NOT RUN**.

## Potwierdzony problem z raportu użytkownika v23 (11 XI 2026)

- `SabotageCC`: `loss`, ostatnie częściowe punkty HUD około
  **−16 800**, bez potwierdzonych końcowych punktów.
  D9 ruch otwierającego otrzymał `score=33` mimo wzrostu
  `ExposureRisk: 59.2117 -> 109.9195`, ponieważ wczesne
  `ChooseRoutePrefix` mogło zakończyć wybór **przed** lokalnym
  filtrem zagrożenia. Następnie D10 `ambush_opening preparations=0`
  i samotny `StandardShot`; reszta oddziału nie była właściwie
  przygotowana do wspólnego otwarcia.
- `ChallengeAbductionGasStation`: `loss`, natywne **−10 600**
  (`mission_final=true`). 32 wykonane rozkazy,
  bez potwierdzonego zaliczenia ani poprawy wobec poprzedniej próby.
- `SabotageTransmitter` / Blood Killer: ręczne `Escape`,
  `outcome=unknown`, HUD **+500 tylko częściowe**; 30 ruchów,
  2 `DevastatingPunchMP`, zero `objective_completed`.
  Ten PR nie zmienia specjalnego celu Berserkera.

## Zmiana #31a

1. `APX_MissionPlanner.ChooseMove`: natywna trasa do celu
   otrzymuje tę samą ocenę `ExposureRisk`, jakiej podlegają
   lokalne pozycje. Jeśli wzrost ryzyka przekroczy
   `Max(12, CurrentRisk*0.25)`, trasa nie jest wykonywana w
   trybie zwykłego marszu. Planer dalej szuka istniejącego
   legalnego lokalnego wariantu, zamiast od razu przyznawać
   sobie sukces lub zatrzymywać cały autoplay. Pilna
   ewakuacja/ratunek/aktywny timer są wyjątkiem. Zerowe
   zagrożenie nie oznacza na pewno bezpiecznej osłony.
2. `APX_SquadPlanner`: zanim zwykły strzał z ukrycia zostanie
   oceniony jako otwarcie zasadzki, estymator sprawdza
   odległość, natywny LOS i dostępny natywny overwatch
   u innych zdolnych do działania żołnierzy oraz osłonę
   strzelca wobec wybranego celu. Brak dwóch wspierających
   może obniżyć punktację otwarcia (maks. 36 plus 10 za
   brak osłony). To **miękka kara**, nie blokada legalnego
   strzału: przy braku dobrej alternatywy wciąż może
   zostać wykonany. Nie obejmuje ataków wręcz Berserkerów
   i nie osłabia ratunku, celu misji ani aktywnego timera.
   Rezerwa liczy się tylko dla zwykłego/pistoletowego overwatch
   i pasującej własnej zdolności reakcji z dostępnymi kosztami.
   Suppression, KillZone i ReserveInterrupt nie stanowią takiego wsparcia.
   Jest to potencjalna gotowość: przyszłe warunki celu reakcji nadal
   rozstrzyga silnik. Konstruktywny strzał zachowuje wynik powyżej progu
   NoPlan także wtedy, gdy nie ma lepszej alternatywy.
3. `APX_Controller.CanUseAction`: przed wybraniem akcji
   musi ona pochodzić z obecnie dostępnej listy silnika
   z `AA_Success` i mieć `Ability.OwnerStateObject` zgodne
   z działającą jednostką. Logi dotąd nie dowiodły używania
   zdolności cudzych żołnierzy; jest to dodatkowy filtr
   zapobiegawczy, nie naprawa udokumentowanego wyjątku.

## Rozszerzenie: zdolności wrogów i wybuchowe osłony

W raportach GasStation ocena ruchu powinna znać nie tylko statyczne
obrażenia podstawowej broni wroga, ale również jego ujawnione z szablonów
zdolności ofensywne. `GetThreatWeights` korzysta teraz z
`APX_EnemyKnowledge.TargetThreat` — zawiera bounded wskaźniki
`Capability_Area`, `Capability_Control` i `Capability_Support`.
Zagrożenia są pobierane **raz na listę kontaktów** w danym wyszukiwaniu
ruchu, nie ponownie na każdym polu. Nie czytamy ukrytego AP, czasu
odnowienia ani decyzji przeciwnika.

Nowy `APX_ExplosiveCoverKnowledge` sprawdza istniejące, jeszcze niezniszczone
`XComDestructibleActor` przy nowej pozycji. Czyta ograniczoną liczbę zdarzeń
`DestroyedEvents` i natywne `GetBlastExtents` dla zdarzeń radialnych; bada
pole żołnierza bez tworzenia tablicy wszystkich pól. Sumuje nominalne dodatnie
`UnitDamage` pasujących zdarzeń jako estymację ryzyka. Nie używa do tego
`GetRadialDamageTiles`, które stock implementuje pętlami UC, ani nie uznaje
samej sumy UI `GetDestroyedDamagePreview` za dokładną prognozę trafienia.
Wraki, stan Dead oraz rozpoczęte/zakończone zniszczenie nie są przyszłą bombą;
płonący, wciąż żywy `_Damaged` może pozostawać zagrożeniem.

Wymaga znanego wroga z potencjalnym atakiem dystansowym/obszarowym w
przybliżonym zasięgu geometrycznym. Pełne rozpoznanie może dostarczyć jego
obecną pozycję, lecz nie jego zamiary, aktualny AP ani ukrytą wiedzę.
**Nie oznacza to**, że przeciwnik wykona taki atak w następnej turze,
ani że obiekt da się zniszczyć jednym trafieniem. Punktacja jest tylko
miękką, ograniczoną karą: maksymalnie 42 jednostki score.

Dla natywnego A* ryzyko samochodu prowokuje poszukanie innej legalnej
pozycji, a oryginalną ścieżkę zachowuje jako awaryjną dopiero po przejściu
kontroli ekspozycji i pozostałych ograniczeń. Jeden budżet sześciu ocen
osłon obejmuje całą decyzję, wszystkie jednostki, prefiks i lokalne warianty.
Każda ocena bada najwyżej pięć pól, 16 obiektów oraz 32 zdarzenia zniszczenia.
Niepełna ocena ma koszt niepewności 42, bez premii za niesprawdzenie.
Dotyczy **również oddziału, który utracił concealment**, np. GasStation.
Aktywne terminy, ratunek, ewakuacja i specjalny sabotaż BerserkerMP
nie mogą zostać zablokowane przez tę preferencję.

Konstruktywny wynik legalnego fallbacku nie może spaść poniżej progu
globalnego NoPlan/OFF wyłącznie przez miękką karę. Nie podnosimy natomiast
wyniku bazowo niekonstruktywnego ruchu i nie pomijamy utraconego ataku.

Nowe źródło `APX_ExplosiveCoverKnowledge.uc` wymaga kompilacji Windows WOTC
SDK. Zielony test Python sprawdza kontrakty źródłowe i matematykę.
W pierwszej próbie A/B sprawdzić koszt sprawdzania
samochodów, zapętlenia w pobliżu osłon i to, czy osłona uznana za
wybuchową rzeczywiście ma wtórne obrażenia. Jeżeli nie, wyregulować
karę na podstawie dowodów, nie na domysłach.

**Odrębna gałąź #38** odpowiada na ofensywny granatnik.
GasStation v23 miała `LaunchGrenade` `AA_Success` dla unit 63486,
lecz wszystkie 355 sprawdzonych centrów nie przeszły filtrów
(`range=262`, `blast=91`). Wśród blokad było
`objective_near_blast / empty_footprint`. PR #45 oddzielnie bada natywny
obrys jednostki i rzeczywiste granice wizualizera przy brakującym footprint.
Kotwica `TileLocation` i stałe dwa pola nie są granicą dowolnego obiektu.
Brak zweryfikowanych granic nadal wymaga odrzucenia kandydatury. Tego kodu
**nie ma w PR #44**; przed następną kompilacją LEAD wskaże końcowy SHA integracji.

## Czego to NIE rozwiązuje

- **#31b** — wybór jednej grupy na podstawie dozwolonych obserwacji,
  staging legalnych OW, kontrolowany opener bez concealment i pamięć celu.
  Samo `AIGroup.IsEngaged()` czyta również wewnętrzną wiedzę AI; ten wariant
  nie stosuje takiej kary. Pełny plan kolejnych grup nie jest wdrożony.
- Ofensywny solver wybuchów wtórnych, ocena synergii całego
  zestawu zdolności i prawdziwy `PlantBomb` są innymi zadaniami.
- Brak gwarancji, że activation scamper uruchomi overwatch,
  ani że ukończenie każdej misji jest możliwe przy obecnym
  zestawie ogólnych plannerów. Brak modyfikacji natywnych
  punktów, amunicji, AP, RNG lub ukrytych zamierzeń wroga.

## Próba A/B

Po review LEAD i kompilacji **jednej** kontrolowanej wersji
odtworzyć ten sam zapis v23 dla `SabotageCC`.
Zmierzyć D1-D10: ryzyko otwierającego, faktycznie wybrany
ruch, liczba przygotowanych OW i strzelców z LOS/cover,
ile natywnych grup rzeczywiście aktywowano i czy doszło
do kolejnej fazy. W GasStation sprawdzić, czy wariant
ogranicza prowokowanie dodatkowych przeciwników na podstawie obserwowanych
aktywacji i ataków. Blood Killer oraz brak PlantBomb pozostają osobnym
testem #29; odrzucony wariant ostatniego AP z #43 nie jest częścią v24.

W **każdej** misji raportować native outcome, wykonanie
wszystkich wymaganych celów i punkty: końcowe potwierdzone,
częściowe albo nieznane. Zielone CI nie zastępuje kompilacji
UnrealScript i rzeczywistej wygranej >0.
