# Materiał po rzeczywistym zatrzymaniu gry w Windows

Launch.log i heartbeat pomagają odtworzyć ostatnie zdarzenia, ale nie pokazują
stosów natywnych wątków. Przy zatrzymaniu całego game thread sam Tick moda
nie może dopisać kolejnej obserwacji. Nie wymuszamy ForceComplete ani
DebugClearHangs: zniszczyłoby to stan potrzebny do ustalenia przyczyny.

## Gdy gra przestanie odpowiadać

1. Pozostawić proces gry uruchomiony. Otworzyć Menedżer zadań przez
   Ctrl+Shift+Esc i przejść do Szczegółów.
2. Wybrać XCom2.exe, prawy przycisk → Utwórz plik zrzutu pamięci
   (nazwa polecenia może różnić się między wersjami Windows).
3. Zachować plik ze ścieżki pokazanej przez Windows. Po około10 sekundach
   utworzyć drugi zrzut i zachować go osobno; jeśli Windows używa tej samej
   nazwy, pierwszy wcześniej przenieść lub zmienić jego nazwę.
4. Zebrać zwykły raport misji oraz zapisać SHA zbudowanych źródeł i moment
   zatrzymania. Zrzuty przekazywać prywatnie, poza publicznym GitHubem.

Dwa zrzuty pozwalają porównać stosy: stałe oczekiwanie na blokadę,
wykonywaną pracę natywnego AI/fizyki albo zatrzymaną wizualizację.
Nie gwarantują ustalenia przyczyny bez symboli. Pełny zrzut bywa znacznie
większy od raportu misji; najpierw zachować go lokalnie. Zawartość pamięci
może zawierać dane prywatne, dlatego nie dołączać jej do publicznych issue.

Nie traktować zwykłego, nadal postępującego oczekiwania wizualizatora jako
potwierdzonego HANG. Ręczne OFF i zakończenie procesu także urywają log.
F8/OFF zatrzymuje kontroler, ale nie wyłącza poprawki szablonu MP zastosowanej
przy starcie. Samo OFF nie jest kontrolowanym porównaniem tego patcha.
