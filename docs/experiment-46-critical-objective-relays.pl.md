# Eksperyment #46 — krytyczny fail objective i diagnostyka przekaźników

Baza: v24, commit \`defdcee43945a0755de6d069d7690cd215c83c63\`.
Wariant diagnostyczny: \`mission-report-v25\`. Status: do przeglądu LEAD,
bez kompilacji Windows WOTC ani odbioru rozgrywki.

## Krytyczna porażka

Własne kryterium PASS jest koniunkcją trzech faktów: wykonano **wszystkie**
obowiązkowe cele, natywna gra zgłosiła \`win\`, a końcowe
\`mission_points > 0\` są potwierdzone. Porażka któregoś celu jest
**krytyczna**, nawet gdy HUD lub końcowy score są dodatnie.

Nowy, tylko odczytujący \`OnObjectiveFailed\` odbiera stock
\`MissionObjectiveMarkedFailed\`, sprawdza źródłowy
\`SeqAct_DisplayMissionObjective\`, obecną misję i zgodność indeksów
puli tekstów, po czym zapisuje pojedyncze
\`APXREC|event=objective_failed|critical=true|objective_id=...\`.
Nie zmienia Kismet, licznika czasu ani natywnego wyniku. Jest to
obserwacja po uruchomieniu F8; jeżeli event wystąpił wcześniej,
recorder może go nie widzieć — brak zapisu NIE dowodzi sukcesu.

\`tools/game_scoring.py\` klasyfikuje taką sesję jako
\`status=fail,reason=critical_objective_failed\`, niezależnie od
\`win\`, \`loss\`, \`unknown\` lub dodatniego wyniku.
\`tools/analyze-mission-log.py\` wyświetla identyfikatory failed
objectives i ostrzeżenie CRITICAL. Dane nadal zawierają osobno
punkty z oznaczeniem \`confirmed/provisional/unknown\`.

## Przekaźniki czasu SabotageTransmitter

Oficjalny podręcznik WOTC potwierdza, że zniszczenie przekaźników
wydłuża czas na podłożenie X4.
\`APX_CombatPlanner.ScoreObjectiveAttack\` dotąd wymagał
\`Helpers.IsObjectiveTarget\`, co **może** odrzucać pomocnicze
urządzenia przedłużające czas. Samo 2 HP nie identyfikuje
przekaźnika i nie uprawnia do ataku w zwykłą osłonę.

Nowa funkcja \`RecordSabotageRelayCandidates\` jest **diagnostyczna**:
raz na turę XCOM w SabotageTransmitter odczytuje
\`XComGameState_Destructible\` z historii i natywne
\`AvailableActions\` żołnierzy. Ograniczenia: maks. 256
skontrolowanych obiektów/20 opisanych, 8 żołnierzy, 128 akcji,
192 referencje celów na turę. W logu zapisuje obiekt, zdrowie,
rzeczywiste TileLocation/wizualizer, flagę \`IsObjectiveTarget\`,
a dla dostępnych akcji: źródłowego żołnierza, szablon zdolności,
\`AA_*\`, ID celu i prawdziwą flagę wrogiego celu.
Wszystkie podejrzane obiekty są oznaczone jako
\`unverified_destructible\`: **nie są automatycznie przekaźnikami**.
Bez działania na silnik, bez dodawania AP ani nowych celów.

Na podstawie logu z tej gałęzi i lokalnego SDK należy ustalić
konkretny archetyp przekaźnika i potwierdzić natywną legalność
ataku dla BerserkerMP. Dopiero następny osobny PR powinien
nadawać premię za rzeczywisty zysk na timerze lub planować
dojście do dostępnego przekaźnika. Jeżeli Berserker nie ma
własnej zdolności, która pozwala go uszkodzić, nie wolno
udawać takiej zdolności ani zmuszać go do nielegalnego ataku.

## Odbiór

Testy źródłowe: \`test_critical_objective_relay.py\`,
\`test_recorder_scoring.py\`, \`test_mission_log.py\`.
Kompilację musi wykonać Windows SDK. W Blood Killer po uruchomieniu
zatwierdzonego commita v25 sprawdzić: natywne przekaźniki,
\`AA_Success\` (albo jego brak), rzeczywistą liczbę
dodatkowych tur, dojście do właściwego miejsca X4 i
\`objective_failed\` w raportowaniu. Przekazać trzy dane:
native outcome, wynik punktowy z pewnością źródła,
wykonanie wszystkich celów.

**Nowy prywatny ZIP z 11.11.2026:** dostęp do kontenerowego
odczytu w tej sesji zgłasza błąd narzędzia. Nie raportować
z niego zmyślonych wyników ani nie publikować logów.
