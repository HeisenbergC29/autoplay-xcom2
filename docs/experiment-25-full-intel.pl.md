# Eksperyment #25: pełna mapa i rozpoznanie żywych przeciwników

Źródło decyzji: użytkownik bezpośrednio potwierdził 6 listopada 2026
pełną wiedzę AI o mapie i pozycjach aktywnych przeciwników.
Baza `5e9d9eacbe1bfd9ea3f6c178c697065b0a7cbc0c` (v19).
Kod oznacza się jako `mission-report-v20`; dokładny zatwierdzony commit
do kompilacji wskazuje LEAD w [issue #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
To zamierzony wyjątek od dawnego założenia „no hidden contacts”.

## Zakres

Domyślnie przy `EnableFullIntel=true` autoplay używa aktualnych pozycji
wszystkich *aktywnych, żywych wrogich jednostek* z tylko odczytywanej
historii. Odrzuca jednostki usunięte z pola walki, kosmetyczne,
cywilów i jednostki niezdolne do działania. Własny żołnierz pod wrogą
kontrolą nadal jest uwzględniany jako zagrożenie, lecz nie jest celem
pościgu ani własnego ostrzału. Pozycje nie są już ograniczone do pola
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

Znana pozycja dalekiego przeciwnika jest informacją dla planowania,
a nie automatycznym dowodem bezpośredniej walki. Ocena bezpośredniego
zagrożenia korzysta z natywnie widocznych kontaktów; pełna lista pozycji
pozostaje dostępna dla oceny ryzyka. Cele misji i ewakuacji są rozpatrywane
przed podążaniem do dalekiego wroga. Bezpieczna propozycja łupu może nadal
konkurować z takim podążaniem, przy zachowaniu pozostałych ograniczeń.
Rutynowy krok trasy zachowuje zapas AP; ewakuacja ma dotychczasowy wyjątek
ostatniej akcji. Trasa A* jest propozycją: jej krok nadal musi przejść
kontrole ruchu, zagrożeń i wsparcia, także dla dalekiego celu bojowego.

**To nie jest walidacja nowych celów w silniku**. Akcje ataku
pochodzą wyłącznie z natywnej listy `AvailableActions`,
`AA_Success`, z realnymi celami, kosztami AP i normalnymi
testami legalności. Nie przyznaje sztucznej amunicji, AP,
premii do trafienia, nie zmienia HP, wyniku misji ani RNG.

## Rewers i ryzyka

Aby powrócić do normalnej mgły w *nowym uruchomieniu misji*
ustaw w `AutoplayXCom2/Config/XComAutoplayXCom2.ini`:
`[AutoplayXCom2.APX_FullIntel]` → `EnableFullIntel=false`.
Planowanie korzysta wtedy ze zwykłej wiedzy o widocznych przeciwnikach
i polach, zamiast ujawniać ich pozycje z historii.
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

## Odbiór na Windows

1. Zbuduj zatwierdzony commit v20 w Windows WOTC SDK;
   zachowaj `.build/mod-make.log` i dokładny SHA.
   Nie instaluj kilku wariantów moda jednocześnie.
2. Włącz misję `ChallengeAbductionGasStation` albo
   `SabotageTransmitter` z wcześniej zachowanej
   kopii zapisu. Sprawdź w logu `mission-report-v20`, pole
   `full_intel_enabled=True` w początku rejestracji oraz
   `Full intel|...enabled=True|map_revealed=True`.
3. Potwierdź odkrycie mapy, drogę AI do wroga za przeszkodą,
   brak rozkazów ataku w niedozwolone cele i prawidłowy
   koniec tury. Sprawdź jednostki pojawiające się później, usunięcie
   martwego celu oraz pilne czynności przy znanym dalekim kontakcie.
   Model jednostki może pozostać niewidoczny mimo wiedzy AI.
4. Zanotuj liczbę decyzji, liczbę ataków, win/loss,
   natywny wynik, nowe zapętlenia i zawieszenia.
   Przekaż ZIP raportu; surowych plików nie publikować
   na GitHubie.
5. Wariant z `EnableFullIntel=false` sprawdź od nowego uruchomienia
   misji, na kopii zapisu i po restarcie gry. F8 wyłącza nowe rozkazy,
   nie przywraca terenu już ujawnionego w tej samej próbie.

SDK API audit i testy Pythona są kontrolami źródłowymi,
a **nie** kompilacją WOTC ani wynikiem rozgrywki.
Kod po poprawkach przeglądu zaliczył 539 testów z prywatnymi wejściami
bez pominięć i audyt 18 klas / 31 nazw zdolności. Końcowe CI i decyzja
są śledzone w PR #26 i issue #27. Kompilacja Windows WOTC SDK i gra v20:
**NIEURUCHOMIONE**. #20 (anty-AoE) i #28 (pilne podejście/leczenie)
pozostają osobnymi zadaniami; bieżąca zmiana nie dowodzi ich rozwiązania.

[Raport bazowy GasStation v19](report-2026-11-06-v19-gasstation.pl.md)
jest porażką z częściowym odczytem końcowym, nie dowodem niemożności misji.
