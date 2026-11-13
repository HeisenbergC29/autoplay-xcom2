# #62 — stale widoczny panel autoplay, runtime v30

## Kontekst i baza

Użytkownik zażądał stałej widoczności menu moda podczas walki.
Baza `main` `189aa3d3aba054109f7ca1405770a2c90b0676e9`,
zawierająca v29 #56, którą użytkownik równolegle kompiluje i testuje.
Nowy PR jest osobny; nie zastępuje testowanego SHA ani wyniku raportu v29.

## Zmiana

`APX_UITacticalControl.AlwaysExpanded` jest opcją config, domyślnie
`true` w `XComAutoplayXCom2.ini`. Przycisk ON/OFF, bieżący status
i wynik punktowy pozostają widoczne na panelu `UITacticalHUD` również
przy nieaktywnym autoplay, po najechaniu/opuszczeniu kursora i po kliknięciu
toggle. `ScheduleCollapse()` przy `true` gasi jedynie pending collapse;
`Collapse()` i `Tick()` mają dodatkowe zabezpieczenia, by nie ukrywać
aktywnej kontrolki. `Expand()` zachowuje `EnableMouseHit` i normalną
pełną przezroczystość. `AlwaysExpanded=false` przywraca wcześniejszy
dwusekundowy collapse/fade/mały wskaźnik bez zmiany zachowania przycisku.

Nie zmienia to ani układu stock UI i menu nadrzędnych, ani reguł pauzy
autoplay. Właściwym zakresem życia widżetu jest ekran taktyczny;
po zdjęciu HUD `Removed()` czyści kontroler i score probe tak samo jak
wcześniej. Mod nie próbuje rysować nad ekranami zakończenia misji,
modalami ani innymi elementami, których nie kontroluje. Wyświetlany
score pochodzi z istniejącego `APX_MissionScore`; guard latent update
i brak niebezpiecznego `GetTotalScore` w HUD pozostają bez zmian.

Runtime `mission-report-v30` jest użyty w starcie rejestratora,
inicializacji HUD, diagnostic MP i testach rewizji; nie zmienia formatu
natywnej punktacji. Zmieniony plik INI ma opis opt-out.

## Weryfikacja

`tests/test_persistent_tactical_panel.py` sprawdza config, zakres
widoczności, klik/score/status, zachowanie opt-out, zgodność z safe
score provider i cleanup HUD. Publiczna CI wykonuje kontrakty źródłowe;
prywatne SDK checks mogą być pominięte. UE3/Flash nie jest tutaj
kompilowany ani uruchamiany, zatem potwierdzenie widoczności i braku
konfliktu z innym UI należy do testu Windows w późniejszej wersji
wskazanej przez LEAD. Brak wpływu na kryterium misji
native victory + official final mission points >0.

## Przekazanie

Po code review LEAD może scalić ten PR. Następna taktyka #31 jest
osobna, może wymagać rebasingu nowego v30 ze względu na wspólny marker
runtime/INI, i nie powinna być dołączana do #62.
