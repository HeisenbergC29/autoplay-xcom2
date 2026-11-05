# Eksperyment #17: ograniczenie odczytów punktacji w HUD

Status: propozycja HELPER do przeglądu LEAD; **nieudowodniona
naprawa zawieszenia**. Baza v18:
`e30bf6a18ac6a35a4644e7b09a91157d85c0f518`.
Powiązania: #15 (poprzednia awaria), #21 (nowe zawieszenie),
#4 (próby Windows) i #17 (przydzielony eksperyment).

## Założenie

Przy włączonym `APX_UITacticalControl` panel statusu odświeża się
co 0,25 s również przy F8 OFF. Dotychczas każde takie odświeżenie
uruchamiało `APX_MissionScore.GetText`, który dla aktualnego
`ChallengeData` woła natywne `GetTotalScore()`. W najnowszej
próbie BerserkerMP v18 było 460 wierszy `GetTotalScore`, czyli 230 par zapisu
pojedynczego odczytu (ScoreType i TotalScore) w okresie
około 160 s. Koincydencja nie dowodzi przyczyny zawieszenia.

W tym wariancie panel statusu zachowuje 4 Hz. Sam **tekst HUD**
jest ponownie odczytywany od razu po zmianie obiektu/indeksu
historii, przy pierwszym pokazaniu panelu, a także okresowo
co około 1 s bez nowego wpisu historii. Nawet przy F8 OFF.
`RecordDisplayedScore` otrzymuje dokładnie ten tekst,
który jest renderowany; rejestrator nadal deduplikuje wpisy.
Zmiana nie buforuje obliczeń natywnych na koniec misji:
`ReadNativeMissionPoints` wywołuje oryginalne `GetText`
i nie korzysta z cache HUD. Nie zmienia żadnej wartości, maksimum,
profilu częściowego `~`, progów sukcesu ani sposobu scoringu.
W razie usunięcia panelu cache jest usuwany wraz z nim.

## Ograniczenia i ryzyka

Przy natywnej zmianie wyniku bez nowego GameState HUD może
wyświetlać poprzednią wartość do około 1 s. Przy szybkich
zmianach GameState odczyt może wciąż występować 4 razy/s;
heurystyka nie gwarantuje stałego globalnego limitu. To
optymalizacja odczytów HUD, nie przywracanie faz silnika
ani hard-watchdog procesu. Nie ruszamy `DevastatingPunchMP`,
`APX_Controller`, zachowania Berserkerów ani innych plannerów.

## Test A/B

1. **A**: na kopii tego samego zapisu zbudować bazę v18
   `e30bf6a18ac6a35a4644e7b09a91157d85c0f518`.
   Zanotować wynik i powtarzalność błędu; zachować raport.
2. **B**: po przeglądzie przez LEAD zbudować *dokładny* HEAD
   tego PR. Bez innych dodatków; restart gry pomiędzy próbami.
   Zachować równoważny scenariusz i ten sam startowy save.
3. Sprawdzić przy F8 ON i OFF, czy wynik nadal jest aktualny,
   czy odczyt ostatnich punktów jest dokładny i czy linie
   `GetTotalScore` występują rzadziej przy stabilnej historii.
4. Oceniać niezależnie: opóźnienie HUD, poprawność końcowych
   punktów, liczbę wywołań, awarie/zawieszenia, liczbę
   zaakceptowanych ataków, zakończenie misji i wynik.
   Sam brak zawieszenia w jednej próbie nie wystarcza do
   ustalenia przyczyny.

## Walidacja

Testy statyczne/numeryczne i publiczne CI nie kompilują
UnrealScript; prywatne SDK i konfiguracje oraz rzeczywiste
Windows WOTC build / gameplay wymagają odrębnej weryfikacji.
