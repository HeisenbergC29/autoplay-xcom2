# Eksperyment #15 — wizualizacja DevastatingPunchMP

V18 integruje PR #16 jako izolowany wariant diagnostyczny, **nie potwierdzoną
naprawę crasha**. Punktem odniesienia jest v17
`ba4550a8495c5c7d504eca681a6465b2c433ae37`.

W źródłach SDK zwykły `DevastatingPunch` ukrywa
`AA_HitResultFailure` dla dwóch alternatywnych efektów obrażeń,
podczas gdy `DevastatingPunchMP` nie ma tych wpisów.
`X2Ability_Impairing` oczekuje pojedynczego węzła obrażeń.
Może to tłumaczyć wcześniejsze redscreeny, ale nie udowadnia
przyczyny późniejszego `ACCESS_VIOLATION`.

W `OnPostTemplatesCreated` poprawka obejmuje tylko wszystkie warianty
trudności `DevastatingPunchMP` z dokładnie dwoma oczekiwanymi efektami
hit/miss i jednym wyzwalaczem `Impairing`. Dopisuje wyłącznie
`HideVisualizationOfResultsAdditional` = `AA_HitResultFailure`.
Nie dotyka hit-roll, obrażeń, miss damage, AP, statystyk, Impairing,
planu taktyki, HUD ani punktacji. Jeśli szablon ma inną strukturę,
poprawka niczego nie zmienia.

Przy starcie v18 log zawiera podsumowanie:
`MP visualization patch|revision=mission-report-v18|templates=N|matched=N|skipped=N`.
`matched` obejmuje zgodne szablony z obydwiema flagami po kontroli, także
takie, które już miały te flagi; nie liczy wyłącznie nowych zmian.
`status=manager_unavailable` oznacza brak kontroli. Dla rozstrzygającej
próby wymagane są `templates > 0`, `matched > 0` i `skipped=0`.
Pominięte szablony mogą dotyczyć wybranej trudności; wtedy wynik jest
nierozstrzygający i podsumowanie wymaga przeglądu. Zero `matched` albo
brak wpisu nie potwierdza, że poprawka działa. Zachowaj log od startu gry,
ponieważ ten wpis powstaje przed F8.

## Porównanie A/B na kopii zapisu

1. Zachowaj nietknięty oryginał crash-save. Wariant A zbuduj z
   dokładnego commita v17 `ba4550a8495c5c7d504eca681a6465b2c433ae37`;
   wariant B z dokładnego commita integracji v18 wskazanego przez LEAD w
   [issue #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
   Każda kompilacja z Windows WOTC SDK; odinstaluj poprzednią paczkę
   i zrestartuj grę przed kolejnym wariantem.
2. W B sprawdź `revision=mission-report-v18` i startupowe `templates > 0`,
   `matched > 0`, `skipped=0`.
   F8 OFF/ON nie zastępuje porównania kompilacji: poprawka szablonu działa
   także przy ręcznych ciosach i pozostaje aktywna przy wyłączonym autoplay.
3. W obydwu wariantach uruchom identyczną kopię zapisu i wykonaj
   `DevastatingPunchMP` na tym samym celu, o ile to legalne.
   Jeśli zapis pochodzi już z późnej fazy, użyj wcześniejszego
   dostępnego save do powtórzenia ciosu. Bez rzeczywistego ciosu próba
   wizualizacji pozostaje nieuruchomiona; późny zapis może służyć osobno
   do badania samej awarii.
4. Porównaj liczbę wystąpień
   `GetNodeOfType found more than one node`, rzeczywiste obrażenia,
   wynik działania, ewentualne `ACCESS_VIOLATION` oraz ostatni
   zaakceptowany rozkaz. Zanotuj dokładne SHA źródeł.
5. Przekaż raporty z obu prób. Brak wcześniejszego redscreen w B
   **nie oznacza automatycznie naprawy późniejszego crasha**.

Testy kontraktowe SDK, kontrole źródłowe, Windows build i gameplay
mają osobne wyniki; nie publikować prywatnego dumpa ani surowych logów.
Integracja v18 zaliczyła 518 testów z prywatnymi wejściami bez pominięć
oraz audyt 17 klas / 31 nazw zdolności. Kompilacja Windows WOTC SDK i
próba v18 w grze: **NIEURUCHOMIONE**. HUD, punktacja i taktyka pozostają
takie jak w bazie A, aby porównanie dotyczyło jednego mechanizmu.
