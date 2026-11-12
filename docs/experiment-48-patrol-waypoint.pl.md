# Eksperyment #48 — aktualny zapisany cel grupy przeciwników

Użytkownik 11 listopada 2026 potwierdził rozszerzenie pełnego rozpoznania
o aktualny cel patrolu. Wariant integracji to `mission-report-v25`, razem
z diagnostyką #47 i #50. Windows WOTC SDK i gra: **NOT RUN**.
Dokładny końcowy SHA i ZIP wskazuje LEAD w issue #4.

## Zakres wiedzy

`APX_PatrolKnowledge` odczytuje wyłącznie obecne
`XComGameState_AIGroup.CurrentTargetLocation` oraz dozwolone pozycje
zweryfikowanych, żywych i aktywnych wrogich członków. Nie wywołuje wyboru
nowego punktu, wrogiej AI ani RNG. Następny punkt może zostać wybrany
losowo albo zmieniony w reakcji na sytuację; nie znamy całej przyszłej trasy.

Po poprawkach LEAD odczyt jest włączony tylko przy `EnableFullIntel=true`
i poprawnym lokalnym graczu XCOM. Nie używa `IsEngaged`,
`HasAbsoluteKnowledge`, prywatnych flag alertu, scampera, celu/interceptu
ani czasu ostatniego wyboru punktu. Pełna mapa i aktualny punkt nie dają
pozostałych ukrytych zamiarów, AP, amunicji ani cooldownów przeciwnika.

Brak tych prywatnych filtrów oznacza, że nie możemy twierdzić, iż dana
grupa jest niezaangażowanym patrolem lub rzeczywiście maszeruje właśnie
do tego pola. Log opisuje **zapisany bieżący punkt**, z nieznanym przyszłym
użyciem. Punkt przy początku współrzędnych nie jest automatycznie pusty;
wymagane są skończone współrzędne i prawidłowe pole świata.

## Ograniczenia pracy i danych

Jedna obserwacja na wartość tury gracza bada ograniczoną liczbę grup
(domyślnie 32, maksymalnie 48) oraz wspólny budżet referencji członków (domyślnie 128, maksymalnie 256).
Limit dotyczy przejrzanych wpisów, także odrzuconych, a nie tylko
opublikowanych wyników. Niepełna grupa nie dostaje wymyślonego środka
ani uznania za zweryfikowaną.

Liczba członków i środek grupy pochodzą z tego samego zweryfikowanego
zbioru aktywnych wrogów. Nie używamy `GetGroupMidpoint`, które może
uwzględniać martwe jednostki. Grupę bez kwalifikującego się wroga
pomijamy. Brakujące/usunięte stany i niewrogie jednostki nie tworzą
aktualnego patrolu. Recorder korzysta z granic historii/misji z #47.

Ta faza udostępnia i rejestruje bieżący punkt do oceny w realnej grze.
**Nie dodaje jeszcze planowania punktu zasadzki ani sekwencji overwatch.**
Natywne AP, zasięg, LOS, dostępne akcje i celowanie nadal rozstrzygają
każdy przyszły atak. Activation scamper nie gwarantuje reakcji overwatch.

## Próba

Po kompilacji końcowego SHA sprawdzić `patrol_group` i `patrol_scan`
w tej samej GasStation co v24: zgodność zapisanych punktów z późniejszym
ruchem oraz to, kiedy punkt się zmienia. Potwierdzić brak tych odczytów
przy `EnableFullIntel=false`, brak wpisów dla martwych/niewrogich grup
oraz zachowanie limitów i czasu decyzji. Rozdzielić obecny punkt od
prognozy całej trasy i od dowodu, że przeciwnik faktycznie tam doszedł.

Następny #31b może oprzeć ograniczony plan kontaktu na potwierdzonych
danych, z legalnym stagingiem, terminem i możliwością przerwania przy
pilnym celu/ratunku. Nie wprowadzać takiego planu do melee-only Blood
Killer na podstawie samej telemetrii. Weryfikować native outcome,
cele i końcowe punkty >0; nowe dane same nie dowodzą poprawy wyniku.

Testy Python/audyt SDK nie zastępują kompilacji i rozgrywki.
Surowe SDK oraz raporty pozostają prywatne.
