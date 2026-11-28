# #139 — rozpoznanie przyczyny postoju bez planu (v54)

Baza f588b5f60f3b23ddc3e81c7f2219eaf8d8f17a92. Wyłącznie diagnostyka.
Źródło danych: zanonimizowane ustalenia LEAD w #139 (bez surowych raportów).

## Ustalenie

Gas Station v50 i v53: porażka t21, -11100. 57/58 przyjętych rozkazów
zgodnych po jednostce, celu i polu końcowym. D56/t16 i D59/t18: ostatnia
zdolna jednostka 2 AP, dwa znane wrogie cele, najlepszy Overwatch 2,
ofensywny skan bez obsługiwanych strzałów i propozycji ruchu; po stop
ręczny Overwatch. Brak dowodu legalnej bezpiecznej drogi w tych stanach.

Kod MakeDecision: bContactSearch = !bVisibleThreats && RecentContacts.Length > 0;
bCombatThreats = bVisibleThreats || bContactSearch, następnie tylko OR
HasCombatThreats. Ten konkretny komunikat no-constructive-action wymaga
!bCombatThreats. Dlatego aktywna gałąź remembered-contact nie wyjaśnia
bezpośrednio tego stopu. Known full intel nie oznacza immediate contact.
W zwykłej gałęzi FindGoal sprawdza immediate threats, aktualne cele misji
i ObjectiveLocation przed fallbackiem pursuit. Cel mapy może wyprzeć
odległy znany kontakt, lecz nie mamy dowodu, że tak było w D56/D59.
Nie zmieniamy priorytetu celu ani nie dodajemy fallbacku.

## Marker no_plan_move_scan

Do 16 wierszy jednostek na faktyczny stop no-constructive-action
(lub istniejący wariant SabotageCC w tej samej gałęzi); omitted jawny.
Nie emituje na normalnych decyzjach ani na ręcznym rozkazie.
Najpierw istniejący StopWithStatus zapisuje autoplay_stop z history/turn,
następnie opcjonalne wiersze skanu. Przy jednym wolnym rekordzie zachowuje
się granica stopu, szczegół skanu może zostać ucięty przez limit. Nie
zwiększamy limitu ani nie rezerwujemy dodatkowego slotu.
Pola: unit, ap, branch, outcome, goal, known, immediate, visible,
remembered, combat_threats, best_score, omitted; w zależności od etapu reason.
Goal to rzeczywiście wybrana gałąź (evac, sweep_control_source,
berserker_focus, native_objective, x4_map_marker_unverified, revealed_focus, immediate_enemy,
known_enemy_sweep, mission_object, map_objective, known_enemy_pursuit,
none). native_objective oznacza dodatni status natywnego resolvera X4;
x4_map_marker_unverified oznacza fallback do znacznika mapy przy statusie 0.
Nie zmieniamy wybranego pola ani wartości celu. Brak legalnego ruchu przed FindGoal nie certyfikuje known=0.
Outcome: not_proposed, outscored, controller_rejected, selected.
Selected oznacza chwilowy najlepszy plan, nie native dispatch.
Controller_rejected oznacza istniejącą bramkę CanUseMove (nie nowy
test legalności native), bez powtarzania jej wywołania.
Reason: no_legal_move, no_goal, reserve_ap_gate, missing_reachable_cache,
no_qualified_route. W tej ostatniej: prefix_found (prefix znaleziony przed
dalszymi filtrami, nie gwarancja bezpiecznej trasy), samples (bounded local
candidate count, nie liczba unikatowych pól); liczniki pierwszego
odrzucenia endpoint_rejected (hazard/visibility/support/cost),
gain_risk_rejected (position gain, risk, score), native_path_rejected
(BuildPathToTile false lub <2), unsafe_path_rejected (pełna trasa),
later_rejected (pozostałe lokalne próbki po powyższych bramkach,
nie dowód jednego konkretnego soft-veto). Nie odczytujemy dodatkowej
ścieżki ani nie przeprowadzamy ponownej oceny. Nieznany wynik prefix
przy false nie rozróżnia nieuruchomienia od odmowy.
Brak markera przy braku ocenionych jednostek nie certyfikuje przyczyny.

## Kontrole i kolejna próba

Automatyczne testy wykonują wybrane rzeczywiste fragmenty UC: priorytet
mapy/pursuit, warunek stop z flagami kontaktu, odmowa native path z mockiem
cache i jej marker, source contract braku dodatkowej selekcji i limitu.
Fixture: ostatni zdolny żołnierz 2 AP, dwa znane cele, cache z nieobsługiwaną
zdolnością podany do rzeczywistych bramek GatherForecasts i no-shot,
odmowa native path, następnie istniejące bramki wyboru kandydatów przy
Overwatch=2, stop predicate i rzeczywista emisja Marker/Emit. Osobny
test przy jednym wolnym rekordzie zachowuje autoplay_stop, a skan
wywołuje zwykły limit. Test obu ścieżek natywnego celu X4 i fallbacku
wykonuje rzeczywisty resolver z kontrolowanym statusem native. Nie jest to cała gra ani
przewidywanie native path. Windows build/game NOT RUN.

W zintegrowanej paczce wskazanej przez LEAD uruchomić Gas Station z tą samą
konfiguracją; przy powtórzeniu postoju przekazać LEAD pola no_plan_move_scan,
offensive_reposition_scan i kontekst decyzji. LEAD porówna map_objective
vs known_enemy_pursuit, etap odrzucenia i czy istniała native trasa.
W razie braku legalnej trasy zatrzymanie pozostaje uzasadnione. Nie
odblokowywać niebezpiecznego ruchu na podstawie liczby znanych wrogów.
Natywny wynik i oficjalna punktacja pozostają odrębnymi dowodami.
