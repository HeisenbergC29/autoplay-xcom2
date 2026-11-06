# Eksperyment #25: pełna mapa i rozpoznanie żywych przeciwników

Źródło decyzji: wyraźna prośba użytkownika z 6 listopada 2026.
Baza `5e9d9eacbe1bfd9ea3f6c178c697065b0a7cbc0c` (v19).
Kod eksperymentalny oznacza się jako `mission-report-v20`.
To zamierzony wyjątek od dawnego założenia „no hidden contacts”.

## Zakres

Przy `EnableFullIntel=true` autopilot używa aktualnych pozycji
wszystkich *aktywnych, żywych wrogich jednostek* z tylko odczytywanej
historii. Odrzuca jednostki usunięte z pola walki, kosmetyczne,
cywilów, nieaktywne jednostki i odzyskiwalnych własnych żołnierzy
pod kontrolą umysłu. Pozycje nie są już ograniczone do pola
widzenia XCOM. Nowe jednostki są uwzględniane w kolejnych decyzjach.

Przy pierwszym utworzeniu HUD kod wywołuje oryginalne metody SDK:
`XComWorldData.InitializeAllViewersToHaveSeenFog(true)` i
`XGBattle.SetFOW(false)`; ponawia zmianę, jeśli gra ponownie
włączy render mgły. Odkrywa to teren. Widoczność modeli wrogów
jest jednak osobnym mechanizmem silnika: AI zna ich lokalizacje,
ale samo odkrycie FOW nie gwarantuje wyświetlenia modeli ukrytych
jednostek na ekranie. Nie przełączamy debugowego
`ForceAllUnitsVisible`, aby nie ingerować w wizualizator
powiązany z wcześniejszymi zawieszeniami.

Planery rozważają pola, których wcześniej nie znały, i
próbują natywnej trasy A* w kierunku znanych, niewidzianych
przeciwników. Ruch nadal podlega zwykłej osiągalności,
pełnej ścieżce, kosztowi, przeszkodom, zagrożeniom, wsparciu
oddziału i `CanUseMove`. Zakres przeszukiwania FOW
zostaje wyłączony, ponieważ cała mapa jest już znana.

**To nie jest walidacja nowych celów w silniku**. Akcje ataku
pochodzą wyłącznie z natywnej listy `AvailableActions`,
`AA_Success`, z realnymi celami, kosztami AP i normalnymi
testami legalności. Nie przyznaje sztucznej amunicji, AP,
premii do trafienia, nie zmienia HP, wyniku misji ani RNG.

## Rewers i ryzyka

Aby powrócić do normalnej mgły w *nowym uruchomieniu misji*
ustaw w `AutoplayXCom2/Config/XComAutoplayXCom2.ini`:
`[AutoplayXCom2.APX_FullIntel]` → `EnableFullIntel=false`.
W trakcie już ujawnionej misji stare „widziane” pola mogą
pozostać ujawnione. To nie jest przełącznik przywracający
dokładnie stan UI sprzed modyfikacji.

Pełna informacja o oddziałach nie eliminuje problemów
nawigacji; daleki przeciwnik za ścianą może pozostać
nieosiągalny, a legalna trasa może nie powstać. Obciążenie
przy wielu jednostkach i przejścia w fazie wroga trzeba
zmierzyć na Windows. Zmiana nie jest potwierdzoną
naprawą wcześniejszego zawieszenia ani automatycznym
zaliczeniem próby.

## Odbiór — po decyzji LEAD

1. Zbuduj zatwierdzony commit v20 w Windows WOTC SDK;
   zachowaj `.build/mod-make.log` i dokładny SHA.
   Nie instaluj kilku wariantów moda jednocześnie.
2. Włącz misję `ChallengeAbductionGasStation` albo
   `SabotageTransmitter` z wcześniej zachowanej
   kopii zapisu. Sprawdź w logu `mission-report-v20` oraz
   `Full intel|...enabled=True|map_revealed=True`.
3. Potwierdź odkrycie mapy, liczbę aktywnych wrogów
   rozpoznaną przez AI, drogę do wroga za przeszkodą,
   brak rozkazów ataku w niedozwolone cele i prawidłowy
   koniec tury. Sprawdź też jednostki spawnujące się później.
4. Zanotuj liczbę decyzji, liczbę ataków, win/loss,
   natywny wynik, nowe zapętlenia i zawieszenia.
   Przekaż ZIP raportu; surowych plików nie publikować
   na GitHubie.

SDK API audit i testy Pythona są kontrolami źródłowymi,
a **nie** kompilacją WOTC ani wynikiem rozgrywki.
