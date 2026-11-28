# #122 — fakty o zainstalowanych zdolnościach

Baza ed53b6e96f6cd936142408b787aabe6d392f9a6d (v54, po review #143).
Pierwotna baza f588b5f60f3b23ddc3e81c7f2219eaf8d8f17a92. Etap odczytu po #125
(statystyki) i #123/#137 (wyposażenie). Bez konsumenta, zmian wyceny,
legalności, priorytetów i dispatch; marker v54 z main pozostaje bez zmian.
Dotychczasowe CapabilityFlags korzysta z wydzielonego klasyfikatora
AreaStyleCapability o tych samych czterech rozpoznawanych klasach.

## Kontrakt ReadUnitAbilities

APX_UnitStats.ReadUnitAbilities(History, HistoryIndex, ObserverID, SubjectID,
AbilityIDs, TemplateNames, SourceItemIDs, AreaStyles, Facts,
UnknownAbilityIDs, UnknownScopes, UnknownClasses).

Tak jak ReadUnitStats i ReadUnitEquipment, wejście musi być bieżącym
autoryzowanym snapshotem lokalnego XCOM. Wrogowie podlegają dotychczasowej
polityce widoczności/full intel. Referencje odczytywane w tym samym indeksie.
Zwrócone true oznacza bieżący/autoryzowany odczyt, nie gotowość zdolności
ani pełne rozpoznanie efektów. False czyści wszystkie osiem tablic.
Pusta lista zainstalowanych zdolności jest prawidłowym wynikiem true.
Duplikaty lub ponad 128 referencji odrzucają cały snapshot.

Cztery tablice wierszy: ID służy wyłącznie do odszukania, TemplateNames
to rzeczywiste DataName, SourceItemIDs to potwierdzone odwołanie do
wyposażonego przedmiotu (0 przy braku/nieznanym źródle), AreaStyles to
nazwa rzeczywistej klasy multi-target. Każdy wiersz ma dziewięć liczb w Facts (indeksy 0–7 zachowane,
nowe pole statusu szablonu na końcu),
w kolejności stałych AbilityFactCount:

| Pole | Znaczenie |
|---|---|
| AbilityPresence | 0 nierozwiązany stan / 1 potwierdzony bieżący stan zainstalowanej zdolności, niezależnie od szablonu |
| AbilitySourceStatus | 0 nieznane / 1 potwierdzony przedmiot / 2 brak jawnego źródła i zadeklarowanego domyślnego slotu w dostępnym szablonie |
| AbilityTargetFlags | bity 1 kontrola, 2 rozpoznany styl AoE, 4 wsparcie; target i multi |
| AbilityShooterFlags | te same klasy efektów, wyłącznie na wykonawcy (bez bitu stylu AoE) |
| AbilityEffectScanStatus | 0 niepełny skan / 1 wszystkie trzy listy przejrzane, ledger nieucięty |
| AbilityAreaStatus | 0 nieznany styl / 1 rozpoznany / 2 brak multi-target style |
| AbilityInputStatus | 0 brak szablonu, limit lub niepełna lista bez pozytywnego dowodu / 1 potwierdzony player-input trigger / 2 kompletna lista bez takiego triggera |
| AbilityUnknownEffectCount | liczba odwiedzonych nierozpoznanych lub pustych wpisów efektów (nie całkowita liczba, gdy skan niepełny) |

| AbilityTemplateStatus | 0 szablon niedostępny / 1 odczytano załadowany szablon |

Nierozwiązany stan ma wyzerowane pola i puste nazwy. Przy poprawnym
stanie, ale braku szablonu, Presence=1 i TemplateStatus=0. Jawne źródło
może mieć SourceStatus=1 i potwierdzony ID; dane zależne od szablonu
pozostają nieznane (zera i puste nazwy). Przy SourceWeapon=0 i braku
szablonu SourceStatus=0, nie 2. Nie zgadujemy DefaultSourceItemSlot.
W liście do 16 triggerów pozytywny dowód ma pierwszeństwo przed null
niezależnie od kolejności; null bez pozytywnego dowodu daje unknown,
a pusta lub kompletna lista bez player-input daje 2. Ponad 16 wpisów
nadal nie jest skanowane. HasPlayerInputTrigger dotychczasowego
konsumenta pozostaje bez zmian.
 Zero bitów oznacza
brak rozpoznanych mechanizmów, nie dowód braku innych możliwości.
Nieznany efekt może być poprawnym efektem gry/moda. Oddzielny ledger
zawiera jego ID zdolności, scope target/multi/shooter i nazwę klasy
(pusta dla null). Nie interpretujemy klasy po nazwie zdolności ani
nie zakładamy, że efekt się powiedzie. Ograniczenia: 32 wpisy na każdą
z trzech list, 256 wpisów ledger dla całego odczytu, 16 triggerów,
64 referencje wyposażenia przy weryfikacji źródła. Przekroczenie budżetu
oznacza odpowiedni unknown, a nie brak efektu. Skan nie uruchamia efektów,
delegatów, warunków celu ani losowania.

## Pochodzenie natywne

- XComGameState_Unit: Abilities i InventoryItems to referencje stanu;
  X2TacticalGameRuleset.InitAbilityForUnit przypisuje ItemRef do
  SourceWeapon i dopisuje referencję zdolności do Unit.Abilities.
- XComGameState_Ability: OwnerStateObject, SourceWeapon i GetMyTemplate.
  Źródło musi być bieżącym elementem inventory, własność i slot muszą
  odpowiadać jednostce, stan nie może być usunięty. Nie wnioskujemy
  po nazwie broni, nie odczytujemy SourceAmmo. Zero SourceWeapon przy
  zadeklarowanym DefaultSourceItemSlot lub brakującym szablonie
  pozostaje unknown. Jawne wyposażone źródło sprawdzamy także wtedy,
  gdy GetMyTemplate zwróci none.
- X2AbilityTemplate: AbilityTargetEffects, AbilityMultiTargetEffects,
  AbilityShooterEffects, AbilityTriggers, AbilityMultiTargetStyle,
  DefaultSourceItemSlot. X2DataTemplate.DataName identyfikuje szablon.
- IsA rozpoznaje wspierane klasy i dziedziczenie: MindControl, Panicked,
  Stunned, Sustained; Marked, SpawnPsiZombie; Radius/Cylinder/Cone/Line.
  Zmodyfikowana zdolność z inną nazwą nie traci klasyfikacji tylko
  z powodu zmiany nazwy. Nie rozpoznajemy automatycznie nowych mechanik.
  Styl nie dowodzi rzeczywistego obszaru, aktywności, legalności ani celu.

## Testy i granice odbioru

Publiczny reader jest wykonywany na kontrolowanych native doubles,
z rzeczywistym przepływem UC i trzema realnymi klasyfikatorami. Testy
obejmują dziedziczenie/zmianę nazw, oddzielny scope efektów, puste i
nierozpoznane wpisy, aktualną wymianę wyposażenia, właściciela, limity,
autoryzację i zmianę indeksu. Regresje po review sprawdzają kompletne,
niepełne i przekraczające limit listy triggerów oraz potwierdzone,
odrzucone i zerowe źródła bez szablonu, a następnie jego odzyskanie
w aktualnym indeksie. Prywatny test sprawdza deklaracje SDK
i przypisania native. Nie wykonuje się native action cache ani gry.

Windows WOTC make na zintegrowanej paczce wskazanej przez LEAD.
W dalszym etapie z konsumentem porównać dwa legalne cele o różnych
załadowanych mechanizmach, w tym modyfikację nazwy przy tej samej
klasie; w debuggerze/raporcie konsumenta potwierdzić SourceWeapon,
flagę i unknown ledger po zmianie wyposażenia. Obecna zmiana sama
nie wywołuje nowego odczytu w decyzjach, więc nie powinna zmienić
wyboru rozkazu ani emitować nowego markera. Windows/game NOT RUN.
