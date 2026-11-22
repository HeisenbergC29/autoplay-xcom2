# Zasadzki na patrole i Overwatch w walce w v48

HELPER przygotował zmianę na bazie `1a4df7b74f3dcb3d2ebc400138069f64efd4cb32`. LEAD połączył ją z diagnostyką X4 i zweryfikował analizator na wcześniejszych misjach. [Przegląd #113](https://github.com/HeisenbergC29/autoplay-xcom2/pull/113)

## Odtworzone dowody v46

Użyto załącznika `AutoplayXCom2-20261121-124810-8a828ea5(1).zip`, bez publikowania jego prywatnych logów. `Logs/Launch.log` zawiera pięć sesji `mission-report-v46`:

| Misja | Logowane obserwacje `patrol_group` | Różne ID grup | Decyzje `patrol_ambush_state` | `patrol_evidence_unknown` | `urgent_mission_preempts` |
| --- | ---: | ---: | ---: | ---: | ---: |
| SabotageCC | 42 | 4 | 86 | 73 | 13 |
| GasStation | 21 | 3 | 62 | 62 | 0 |
| Cemetery | 63 | 5 | 153 | 153 | 0 |
| TerrorBar | 28 | 5 | 91 | 91 | 0 |
| Blood Killer / SabotageTransmitter | 45 | 3 | 64 | 0 | 64 |
| Razem | 199 | — | **456** | **379** | **77** |

Każda z 456 ocen zakończyła się z `group=0`. Rejestrator widział współrzędne waypointów. Zapis v46 nie podaje przyczyny odrzucenia poszczególnych grup. W v48 rejestrujemy źródło potwierdzenia patrolu albo powód braku takiego potwierdzenia.

Analizator v48 odczytał 88 985 rekordów z ośmiu sesji w tym archiwum, łącznie z kopiami wcześniejszych logów. Zachował wynik oceny każdej misji. W pięciu bieżących sesjach v46 odtworzył 124 rozkazy Overwatch AI, 130 uzbrojeń i 37 rozstrzygniętych strzałów reakcyjnych. Żadnej z historycznych sesji nie przypisał zasadzki na konkretny patrol.

## Czekanie na patrol

Limit obejmuje trzy potwierdzone tury całej drużyny w jednym epizodzie zasadzki. Zajęcie pozycji, kolejny wartownik i nowy waypoint tej samej grupy same nie zużywają i nie odnawiają limitu. Gra potrafi sama przekazać kolejkę po wydaniu ostatniego AP. Przy odbiorze trzeba sprawdzić zarówno tę ścieżkę, jak i jawne zakończenie tury przez mod.

Podstawę oceny ruchu daje historia już wykonanego ruchu oraz stan grupy odczytany z gry. W dostarczonym SDK procedura `XComGameState_AIPlayerData.UpdateGroupData` czyści obie listy grup i w kodzie skryptowym odbudowuje tylko `GroupList`. Z kolei `XGAIBehavior` w fazie zielonego patrolu sprawdza rejestr nawigatora. To wyjaśnia, dlaczego same wpisy o waypointach w raporcie v46 były niewystarczające. Dokładną przyczynę odrzucenia grupy w konkretnym przebiegu pokaże dopiero nowy raport.

## Użyteczność Overwatch w walce

W TerrorBar w turze 7 trzech żołnierzy uzbroiło Overwatch i żaden nie strzelił. Ostatnie obserwacje ich podstawowych ataków zawierały `AA_NoTargets`. Sam fakt, że ktoś z drużyny widział Shieldbearera, nie rozstrzyga, czy któryś z tych trzech żołnierzy miał lepszą akcję za te same AP.

Przy ocenie rezerwy mod sprawdza bieżący cel, wariant reakcji i broń danego żołnierza. Pod uwagę wchodzą zasięg broni, osobista widoczność lub Squadsight dla Long Watch oraz warunki celu dla reakcji. Bieżąca pozycja wroga nie przesądza, czy poruszy się on w zasięgu. Wartość rezerwy nadal konkuruje z dostępnym strzałem, ruchem, wsparciem i działaniem na rzecz celu misji. W analizie niewykorzystanego Overwatch warto cofnąć się również do wcześniejszej decyzji o ustawieniu strzelca.

## Jak czytać wynik zasadzki

Dla potwierdzonego oczekiwania lub zaakceptowanego strzału otwierającego raport zestawia skład wartowników w grze przed przekazaniem tury lub otwarciem walki z późniejszymi strzałami oddanymi do członków tej grupy. Liczy żołnierzy, w tym tych, którzy spudłowali. Ten sam wartownik może powiększyć licznik tylko raz. Raport wskazuje także rozpoznane ręczne uzbrojenia i ogień zwrotny. Przy niejednoznacznym wydaniu punktu rezerwy albo luce w zapisie wynik może pozostać nieustalony.

Wybór pełnej salwy w `patrol_overwatch.windows` oznacza, że wszyscy wartownicy z danej obserwacji wydali rezerwę Overwatch na strzał do członka wybranego patrolu. Sam zapis strzału nie rozstrzyga, czy wyzwolił go ruch przeciwnika. Raport osobno wskazuje potwierdzoną śmierć ostatniego członka patrolu po obserwowanym ataku drużyny na jego bezpośredni cel. Strzał otwierający może w ten sposób zakończyć okazję, zanim zareaguje pierwszy wartownik. Brak reakcji wymaga porównania z przebiegiem walki.

W tej samej turze mod może rozważyć powrót na pole opuszczone w ukryciu, jeśli po ujawnieniu żołnierza droga przechodzi kontrole bezpieczeństwa, zachowuje AP i daje wyraźnie lepszą prognozę strzału. Po ruchu gra ponownie sprawdza rzeczywisty cel. W późniejszych turach zwykły powrót pozostaje możliwy.

## Próba na Windows

1. Zbudować paczkę wskazaną w #4. Przy wyniku 0 błędów i 0 ostrzeżeń wystarczy potwierdzenie. W logu sesji sprawdzić `mission-report-v48`.
2. W misji bez presji czasu pozostawić autoplay włączony przez kontakt z patrolem. Sprawdzić spójność ID grupy, potwierdzenie ruchu, liczbę faktycznych tur oczekiwania i moment porzucenia planu. Zmiana celu ruchu tej samej grupy nie odnawia limitu. Przy nieruchomej grupie, pilnym celu albo braku dowodów zapisać powód wyjścia. Brak zweryfikowanego ruchomego patrolu to brak okazji do sprawdzenia zasadzki.
3. Dla otwarcia lub oczekiwania z uzbrojonymi wartownikami porównać ich ID z ID strzelców i grupami faktycznych celów. Pełne wykorzystanie wymaga strzału każdego wartownika do członka wybranego patrolu. Pudło też jest strzałem. Odnotować ręczną interwencję i urwany zapis. W walce porównać niewykorzystaną rezerwę z dostępnymi akcjami tego samego żołnierza.
4. Przy powrocie na wcześniej odwiedzone pole porównać koszt AP, zmianę sytuacji, bezpieczeństwo trasy i kolejną akcję. W v46 wszystkie cztery takie powroty odbyły się w późniejszych turach. W Cemetery powrót obniżył szacowaną ekspozycję z 83,60 do 8,26 i umożliwił próbę strzału.
5. W SabotageCC zebrać raport przy podłożeniu X4 lub zatrzymaniu. Jeśli gra zakończy misję, przejść do następnej i sprawdzić, czy proces nadal działa. Odnotować samodzielność, natywne zwycięstwo lub porażkę oraz końcowe punkty za tę konkretną misję. [Próba X4](e2e-sabotagecc-v44.pl.md)

Wyniki z Windows i obserwacje rzeczywistego starcia będą zapisane w [próbie #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
