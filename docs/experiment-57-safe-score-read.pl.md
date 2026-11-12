# #57 — bezpieczny odczyt punktacji, v28

Baza v27: `1575550c495dff2b11406f6b3731ae14a11669b9`.
Implementacja LEAD w PR #58. Windows WOTC SDK/game v28: **NOT RUN**.

## Ustalona ścieżka awarii

Raport v27 Blood Killer kończy rzeczywisty crash po X4/relay i prawidłowym
potwierdzeniu końca tury. Zrzut i dokładnie użyty XCom2.exe są zgodne:
PE timestamp1645568762, SizeOfImage0x20C7000, RSDS GUID
02d7795e-a8cd-4c92-b5d5-5198a23518de/age1. Odtworzono28 ramek AMD64
z właściwych .pdata/.xdata, a nie przez skan adresów stosu. UFunction/FFrame
potwierdzają łańcuch:

`APX_UITacticalControl.Tick → UpdateStatus → GetDisplayedScoreText →
APX_MissionScore.GetText → XComChallengeModeManager.GetTotalScore →
przebudowa StateObjectCache → ObjectIDToGameStatesIndex`.

Natywny exec GetTotalScore zidentyfikowano również niezależnie przez tabelę
rejestracji w EXE. Błąd READ w XCom2.exe+0x4A62F6 wynika z nieprawidłowego
indeksu 16-bajtowego wpisu mapy. Obiekt potwierdzono jako XComGameState,
mapa to ObjectIDToGameStatesIndex, przetwarzany obiekt to Player/ObjectID3.
Pierwszy caller+0xCE2311 dopisuje obiekt do agregatu historii.

To ustala konkretny callback i wymuszoną przebudowę cache. Nie ustala
wszystkich okoliczności uszkodzenia indeksu ani nie dowodzi, że wcześniejsze
zawieszenie v26 miało identyczną przyczynę. Różne wskaźniki w exception
context i późniejszej pamięci dumpu nie są same dowodem race/use-after-free.
Surowe MDMP/EXE/pamięć i ścieżki użytkownika pozostają prywatne.

## Usunięcie wymuszonego agregatora

GetTotalScore/GetTotalScoreFromHistory nie są już wywoływane przez mod.
Kod natywny GetTotalScore sumuje AddedPoints aktualnych
XComGameState_ChallengeScore, pomijając CMPT_None i CMPT_TotalScore.
TotalScore służy jako kontrolny rollup, nie kolejna nagroda; LadderBonus
nie jest składnikiem tej sumy. Nowy reader odtwarza tę samą arytmetykę na
zatwierdzonych stanach gry, bez jawnej przebudowy cache. Pusty zbiór daje
natywne0 wyłącznie w rzeczywistym trybie ChallengeData. Po4096 wpisach
albo nieprawidłowym obiekcie zwraca unknown, nigdy subtotal jako pełny wynik.

Natywny agregator i domyślny iterator korzystają z tej samej mapy typów
bieżącej historii; nie dodajemy wyszukiwania dawnych misji. Standardowy
iterator pomija obiekty bRemoved, podczas gdy surowa natywna pętla nie
sprawdza tej flagi. SDK używa tego iteratora także w SetTempScoreData;
nie ustalono przepływu usuwającego ChallengeScore w tych próbach.
Równoważność arytmetyki dotyczy aktualnych aktywnych wpisów, a nie dowolnie
uszkodzonej historii z usuniętymi rekordami punktowymi. W próbie porównać
HUD z końcowym wynikiem gry; sam HUD nie potwierdza wyniku końcowego.

Legacy nadal używa CumulativeScore minus natywna baza początku misji.
Porównawcza ocena nadal ma tyldę i częściowe pokrycie. Nie zmieniamy
wartości nagród/kar, nie przyznajemy punktów i nie wymyślamy maksimum.
Natywne API maksimum jest odczytywane do pierwszej poprawnej wartości,
wyłącznie za wspólnym guardem. Oddzielny cache maksimum zachowuje granice
historii, startu, misji i szczebla.

## Odroczenie podczas latent update

Przed wejściem w historię provider wymaga istniejącego tactical ruleset oraz
obu warunków: !BuildingLatentGameState i !IsDoingLatentSubmission().
Sam drugi warunek nie wystarcza: stock Tick najpierw stwierdza koniec
pracy wątku, wykonuje EndLatentUpdate i dopiero zeruje BuildingLatentGameState.
Oba pola/API są publicznie czytelne w SDK. Guard obejmuje też porównawczą
ocenę i odczyt dla rejestratora; nie zależy od F8/OFF ani nazwy drużyny.

HUD podczas odroczenia zachowuje tylko wcześniej wyświetlony tekst z tej
samej historii. Pierwszy odczyt/inna historia daje unavailable. Odroczenie
nie wywołuje GetCurrentHistoryIndex ani providera, nie resetuje terminu
odświeżenia i nie emituje hud_score jako świeżej obserwacji. Po uspokojeniu
historii standardowe odświeżenie następuje przy najbliższym należnym statusie.
Bezpośredni ReadNativeMissionPoints zwraca wtedy unknown, zamiast starej
liczby oznaczonej jako świeże/końcowe punkty.

## Weryfikacja i próba

Testy wykonują rzeczywiste helpery UC: signed awards/penalties, pomijanie
rollup i None, obie flagi oraz okno zakończenia wątku przed main-thread
cleanup. Kontrakty sprawdzają kolejność guardów, deferred HUD i brak
publikowania subtotal/stale jako pełnych punktów. SDK kontrakt wiąże guard
z kolejnością stock Tick. Testy źródeł nie są symulacją natywnego wyścigu.

Po buildzie dokładnego końcowego SHA z #4 powtórzyć tę samą Blood Killer:
wykonane relay/X4, dalsza faza obcych i Sweep aż do natywnego końca.
Sprawdzić aktualizację HUD po latent update, poprawność punktów i brak
starej wartości zapisanej jako nowa. Próba projektu wymaga native victory
i znanego końcowego wyniku>0. Ponowny crash wymaga nowego dumpu/logu,
bo usunięcie tej ścieżki nie wyklucza innych przyczyn.
