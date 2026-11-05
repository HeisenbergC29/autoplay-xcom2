# Eksperyment #15 — wizualizacja DevastatingPunchMP

To jest izolowany wariant diagnostyczny, **nie potwierdzona naprawa
crasha**. Punktem odniesienia jest v17
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

## Porównanie A/B na kopii zapisu

1. Zachowaj nietknięty oryginał crash-save. Wariant A zbuduj z
   dokładnego commita v17 `ba4550a...`; wariant B z HEAD tego PR.
   Każda kompilacja z Windows WOTC SDK; odinstaluj poprzednią paczkę
   i zrestartuj grę przed kolejnym wariantem.
2. W obydwu wariantach uruchom identyczną kopię zapisu i wykonaj
   `DevastatingPunchMP` na tym samym celu, o ile to legalne.
   Jeśli zapis pochodzi już z późnej fazy, użyj wcześniejszego
   dostępnego save do powtórzenia ciosu.
3. Porównaj liczbę wystąpień
   `GetNodeOfType found more than one node`, rzeczywiste obrażenia,
   wynik działania, ewentualne `ACCESS_VIOLATION` oraz ostatni
   zaakceptowany rozkaz. Zanotuj dokładne SHA źródeł.
4. Przekaż raporty z obu prób. Brak wcześniejszego redscreen w B
   **nie oznacza automatycznie naprawy późniejszego crasha**.

Testy kontraktowe SDK, kontrole źródłowe, Windows build i gameplay
mają osobne wyniki; nie publikować prywatnego dumpa ani surowych logów.
