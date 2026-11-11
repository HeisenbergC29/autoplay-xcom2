# Eksperyment #31a — osłonięte otwarcie walki i kontrola ryzyka tras

Baza `64c28e76b035bcda92a0ecc902f38ed5c889f88e` (v23).
Wariant roboczy `mission-report-v25` — numer porządkowy zakłada wcześniejszą
integrację osobnego PR #43/v24. Jeżeli LEAD zmieni kolejność, trzeba
zaktualizować rewizję na aktualnym `main` przed scaleniem. Windows SDK
compile / test w grze tego PR jeszcze **NOT RUN**.

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
  (`mission_final=true`). 32 wykonane rozkazy, w tym
  `MedikitHeal` x1, ale także wielokrotny kontakt z przeciwnikami.
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

Nowy `APX_ExplosiveCoverKnowledge` bierze pod uwagę faktycznie
istniejące `XComDestructibleActor` z `HasRadialDamage()` i
`GetDestroyedDamagePreview() > 0`. Ocenia pięć pól wokół wybranego
miejsca i sprawdza, czy pole żołnierza należy do natywnej listy
`GetRadialDamageTiles`. Wymaga znanego wroga z możliwym atakiem
dystansowym/obszarowym; przy włączonym pełnym rozpoznaniu może również
brać pod uwagę jego obecnie znaną pozycję przed aktywacją podu.
**Nie oznacza to**, że przeciwnik wykona taki atak w następnej turze,
ani że obiekt da się zniszczyć jednym trafieniem. Punktacja jest tylko
miękką, ograniczoną karą: maksymalnie 42 jednostki score.

Dla natywnego A* ryzyko samochodu prowokuje poszukanie innej legalnej
pozycji, a oryginalną ścieżkę zachowuje jako awaryjną. W lokalnym
wyszukiwaniu tylko pierwsze sześć obiecujących endpointów otrzymuje
kosztowną ocenę otoczenia — reszta ma małą karę niepewności. Dotyczy
**również oddziału, który utracił concealment**, np. GasStation.
Aktywne terminy, ratunek, ewakuacja i specjalny sabotaż BerserkerMP
nie mogą zostać zablokowane przez tę preferencję.

**Zastrzeżenie produkcyjne:** odczyt `GetRadialDamageTiles` jest native,
a nowe źródło `APX_ExplosiveCoverKnowledge.uc` wymaga osobnej kompilacji
Windows WOTC SDK. Zielony test Python gwarantuje tylko kontrakty
źródłowe i matematykę. W pierwszej próbie A/B sprawdzić koszt sprawdzania
samochodów, zapętlenia w pobliżu osłon i to, czy osłona uznana za
wybuchową rzeczywiście ma wtórne obrażenia. Jeżeli nie, wyregulować
karę na podstawie dowodów, nie na domysłach.

**Odrębna gałąź #38** odpowiada na ofensywny granatnik.
GasStation v23 miała `LaunchGrenade` `AA_Success` dla unit 63486,
lecz wszystkie 355 sprawdzonych centrów nie przeszły filtrów
(`range=262`, `blast=91`). Wśród blokad było
`objective_near_blast / empty_footprint`. Bezpieczny fallback na
`XComGameState_Destructible.TileLocation` jest rozwijany oddzielnie,
bez pozwalania na niezweryfikowane eksplozje łańcuchowe. Tego kodu
**nie ma w tym PR**.

## Czego to NIE rozwiązuje

- **#31b** — pełna sekwencja `XComGameState_AIGroup`
  (wybór tylko jednego niezaangażowanego podu, staging
  legalnych OW, kontrolowany opener bez concealment,
  długotrwała pamięć celu i status `IsEngaged()`).
  Tego nie należy uznawać za już zaimplementowane.
- Przyjazne/niebezpieczne obiekty wybuchowe w obronie,
  ocena synergii całego zestawu zdolności i prawdziwy
  `PlantBomb` są innymi zadaniami.
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
ogranicza prowokowanie dodatkowego podu (pod-ID z SDK,
a nie intuicyjnie estymowane klastery). Blood Killer
testować tylko w odrębnej gałęzi #43 z priorytetem PlantBomb.

W **każdej** misji raportować native outcome, wykonanie
wszystkich wymaganych celów i punkty: końcowe potwierdzone,
częściowe albo nieznane. Zielone CI nie zastępuje kompilacji
UnrealScript i rzeczywistej wygranej >0.
