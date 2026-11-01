# Taktyka: aktualizacja do prób Gatecrashera

Według najnowszego zgłoszenia użytkownika mod już wydaje rozkazy, ale przegrywa
Gatecrasher na Legendzie i Dowódcy. Ta aktualizacja zmienia planowanie walki.
Nie jest potwierdzeniem wygranej: nowy kod wymaga kompilacji i próby w grze.
Profil docelowy pozostaje ten sam: Steam XCOM 2 Collection, War of the Chosen,
oficjalne DLC i wyłącznie AutoplayXCom2, bez Highlandera.

## Zmiany

- Osłona jest oceniana względem przeciwników widocznych dla całego oddziału.
  Odsłoniętego boku nie równoważy kilka kierunków z pełną osłoną; ranny żołnierz
  otrzymuje większą karę za zagrożenie.
- Ruch uwzględnia możliwość flankowania, wysokość, dystans wsparcia i odstępy
  między żołnierzami. Nie wymienia bezpiecznej pozycji na wyraźnie bardziej
  zagrożoną tylko dla potencjalnej flanki. Flanka jest oceną geometrii;
  nie zastępuje natywnego sprawdzenia widoczności i trafienia po ruchu.
- Strzały uwzględniają pancerz, pozostałe HP i tarczę, szansę zabicia oraz koszt
  zdolności. Dobicie aktywnego wroga ma większą wartość niż nadmiarowe obrażenia.
  Po każdej akcji kontroler ponownie ocenia dostępne działania całego oddziału.
- Ruch ofensywny i eksploracja zachowują punkt akcji na odpowiedź. Ruch ostatnim
  AP w walce służy wyraźnemu ograniczeniu zagrożenia. Eksploracja nie działa,
  gdy oddział widzi przeciwnika, i ogranicza oddalanie od wsparcia.
- Granat może zostać użyty przeciw pojedynczemu celowi, jeśli minimalne
  przewidywane obrażenia wystarczają do zabicia. Dodatkowa wartość otwarcia osłony
  wymaga sojusznika z dostępnym strzałem; nie zakłada pewnego zniszczenia terenu.
  Kontrole bezpieczeństwa sojuszników, cywilów i celów misji pozostają aktywne.
  Przy zaawansowanej opcji `ExplosiveFalloff` podgląd SDK nie uwzględnia spadku
  obrażeń z odległością, więc automat nie uznaje takiego granatu za pewne dobicie.
- Kontroler blokuje powroty żołnierza do odwiedzonych pozycji w tej samej turze.
  Log decyzji zawiera wynik oceny, AP przed akcją oraz koniec trasy ruchu.

To heurystyki. Nie modelują całej następnej tury obcych, wszystkich możliwych
podów ani idealnej kolejności wszystkich akcji. Nie odczytują ukrytych pozycji
przeciwników i nie zmieniają AP, trafień ani obrażeń gry.

## Kompilacja z zachowanym SDK

Przy każdej aktualizacji rozpakuj nowy komplet źródeł do pustego katalogu.
Nie jest potrzebny stary pobrany folder projektu. Zachowane SDK oraz jego
zbudowane pakiety bazowe są używane ponownie.

W PowerShell przejdź do nowo rozpakowanego katalogu, który zawiera `tools` oraz
`AutoplayXCom2`, i uruchom (dopasuj ścieżki do swojej biblioteki Steam):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\build.ps1' `
  -SdkPath 'C:\Program Files (x86)\Steam\steamapps\common\XCOM 2 War of the Chosen SDK'
```

Jeśli baza SDK była już zbudowana, pomiń `-BuildBase`. Dodaj ten przełącznik
tylko wtedy, gdy skrypt zgłosi brak bazowych pakietów w nowym lub naprawionym SDK.
Skrypt odświeża własne oznaczone katalogi moda w SDK, a nie całą instalację SDK.
Gdy katalog już istnieje bez znacznika własności, skrypt zatrzyma się zamiast
nadpisać nieznane pliki; najpierw zachowaj je poza tym katalogiem.

Po udanej kompilacji zainstaluj **nowy** `dist\AutoplayXCom2.zip` zgodnie
z `AutoplayXCom2\INSTALL.pl.md`. Możesz też dopisać do polecenia:

```powershell
-GamePath 'C:\Program Files (x86)\Steam\steamapps\common\XCOM 2\XCom2-WarOfTheChosen'
```

Opcja instalacji również chroni zastany katalog bez znacznika własności. Przy
ręcznej aktualizacji zachowaj poprzedni folder moda poza `Mods`, a następnie
wypakuj nowy ZIP do `Mods`. Włącz tylko jedną kopię moda i uruchom grę ponownie.

**Przed usunięciem pobranych źródeł zainstaluj mod albo skopiuj wynikowy ZIP
poza ich folder.** Warto zachować też `.build\mod-make.log`. Zainstalowany mod
działa niezależnie od pobranego repozytorium. Zachowaj SDK, `Development\SrcOrig`,
bazowe źródła i skompilowane pakiety SDK; nie trzeba ich usuwać ani pobierać ponownie.
ZIP w katalogu `release` jest dawną wersją 0.1.0-alpha, bez tych zmian.

## Próby odbiorcze

Uruchom osobny zapis bez Ironmana. Wyniki zapisuj jako PASS, FAIL albo
NIEURUCHOMIONY. Najpierw sprawdź kompilację: świeży `.u`, brak błędów i odrzuconych
ustawień konfiguracyjnych. Następnie:

1. Gatecrasher na Dowódcy i Legendzie: kilka różnych map lub początkowych zapisów,
   bez ręcznych rozkazów po włączeniu. Zapisz wynik misji, straty, rany i liczbę tur.
2. Pełna osłona od dwóch wrogów, otwarta flanka od trzeciego: żołnierz nie powinien
   traktować tej pozycji jako bezpiecznej; sprawdź również żołnierza rannego.
3. Dwóch żołnierzy z dostępnym strzałem, wróg z małą liczbą HP: sprawdź dobijanie
   zamiast rozdzielania obrażeń między wszystkie cele i zmianę planu po pudle.
4. Flankowanie: lepsza pozycja z drugim AP na strzał, a obok flanka bez osłony
   pod ostrzałem kilku wrogów. Automat powinien odrzucić niebezpieczne obejście.
5. Ostatni AP: brak dalszej eksploracji i pogoni za flanką; dopuszczalny odwrót
   wyraźnie zmniejszający zagrożenie, strzał lub legalna obrona.
6. Granaty: pojedynczy cel do pewnego dobicia, pojedynczy zdrowy cel i grupa;
   sojusznik/cywil obok celu musi nadal wykluczać niebezpieczny wybuch.
7. Po walce: oddział idzie dalej z zachowaniem wsparcia, bez ruchu A–B–A i bez
   stałego oczekiwania po wykorzystaniu pierwszych AP.

W razie problemu zachowaj zapis sprzed złej decyzji i `Launch.log` z
`<Dokumenty>\My Games\XCOM2 War of the Chosen\XComGame\Logs`.
Wpisy `AutoplayXCom2` zawierają wybraną akcję, ocenę oraz AP. Nowy log kompilacji
jest potrzebny, jeśli SDK odrzuci kod. Testy Python sprawdzają scenariusze
numerycznych heurystyk i kontrakty źródeł; nie uruchamiają silnika gry.

Po udostępnieniu przez użytkownika folderu `Src` wszystkie 70 testów Python
przeszło bez pominięć, w tym trzy sprawdzające oryginalny układ HUD-u.
Kontrola odwołań potwierdziła dziewięć klas moda i 27 nazw zdolności;
sprawdzono również deklaracje nowych wywołań w źródłach SDK.
Nadal nie jest to kompilacja Windows ani próba w grze.
