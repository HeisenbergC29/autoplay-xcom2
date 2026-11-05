# Eksperyment #17: ograniczenie odczytów punktacji w HUD

V19 integruje PR #22 jako osobny eksperyment, **nie potwierdzoną naprawę
zawieszenia**. Baza A to v18:
`e30bf6a18ac6a35a4644e7b09a91157d85c0f518`.
Powiązania: #15 (wcześniejsza awaria), #21 (zawieszenie v18),
#4 (próby użytkownika), #17 (cache HUD) i #23 (integracja v19).

## Założenie i granice

Panel statusu odświeża się co około 0,25 s również przy F8 OFF.
Dotychczas każdy taki odczyt tekstu uruchamiał `APX_MissionScore.GetText`,
który przy `ChallengeData` wywołuje natywne `GetTotalScore()`.
Według analizy HELPER w #21, w v18 zastosowano poprawkę MP i wykonano dwa
ciosy bez dawnego redscreen, lecz później wystąpiło zawieszenie. Ukryty
HUD w fazie wroga ani częstość odczytów nie ustalają jego przyczyny;
nie jest to potwierdzenie kolejnego wyjątku ze starej awarii v17.
LEAD przegląda to przekazanie i kod, bez niezależnej analizy nowego logu.

V19 buforuje tylko **tekst HUD**. Zmiana obiektu lub indeksu historii
odświeża go na następnym odświeżeniu statusu, około 0,25 s; pierwszy odczyt
nie korzysta z cache. Przy stabilnej historii odczyt jest okresowy,
co około 1 s plus opóźnienie planowania UI. Mechanizm działa przy OFF.
`RecordDisplayedScore` zapisuje dokładnie tekst pokazany na ekranie.
`ReadNativeMissionPoints` nadal wywołuje oryginalne `GetText` i omija cache
HUD; wynik końcowy nie pochodzi z bufora. Formatowanie, maksimum,
częściowy profil `~` i kryterium wyniku > 0 pozostają takie same.
Cache znika wraz z panelem.

Przy częstych zmianach historii odczyty mogą nadal występować około 4 Hz;
nie jest to globalny limit wywołań natywnego API. Poprawka MP, AI,
Berserkerzy i inne planery pozostają jak w A. Zmiany formacji #20 oraz
poprawki PR #11 są poza tym wariantem. V19 nie wymusza końca tury,
widoczności HUD ani przełączenia faz silnika.

## Rozpoznanie wariantu i pomiar

W B sprawdź `revision=mission-report-v19` w rejestratorze oraz wpis:
`HUD score polling|revision=mission-report-v19|stable_interval_seconds=1.0|status_interval_seconds=0.25|history_invalidation=true`.
To opis aktywnej konfiguracji, nie dowód zmniejszenia liczby wywołań
w konkretnej scenie. Wpis MP również identyfikuje v19; sam mechanizm
wizualizacji pozostaje taki jak w bazie v18.

Do porównania częstości natywnego odczytu licz podsumowania
`GetTotalScore - TotalScore:` w równoważnym okresie. Jedno wywołanie może
wypisać wiele wierszy ScoreType, dlatego liczba wszystkich linii ani stałe
parowanie wierszy nie są ogólną miarą liczby wywołań. Oceniaj osobno
odcinki stabilnej historii i odcinki wielu nowych stanów.

## Porównanie A/B na kopii zapisu

1. **A:** zbuduj dokładne v18
   `e30bf6a18ac6a35a4644e7b09a91157d85c0f518`.
   Zanotuj powtarzalność problemu i zachowaj raport.
2. **B:** zbuduj dokładny commit integracji v19 wskazany przez LEAD w
   [issue #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
   Instaluj osobne pakiety i restartuj grę. Użyj kopii tego samego zapisu,
   tych samych ustawień i równoważnych działań. Nie dodawaj innych zmian.
3. Sprawdź wynik HUD przy F8 ON i OFF, zmianie historii i stabilnej historii,
   jego ewentualne opóźnienie oraz poprawność końcowych punktów. F8 OFF
   nie oznacza wyłączenia moda, cache lub wszystkich odczytów rejestratora.
4. Porównaj częstość podsumowań natywnego odczytu według powyższej zasady.
   Nie wymagaj spadku do 1 Hz przy częstych zmianach historii.
5. Zapisz osobno zawieszenie, awarię procesu, postęp faz, ostatni przyjęty
   rozkaz i wynik misji. Zachowaj raporty z SHA źródeł. Sam brak zawieszenia
   w jednej próbie nie ustala przyczyny. Zgłoszona poprawa bez moda jest
   wartościową obserwacją, ale nie zastępuje kontroli tego samego zapisu.

## Walidacja

Przejrzany PR #22 i kod integracji v19 zaliczyły 524 testy z prywatnymi
wejściami bez pominięć; audyt potwierdził 17 klas / 31 nazw zdolności.
Końcowe publiczne CI integracji jest śledzone w PR #24. Publiczne CI
PR #22: 464 PASS / 60 SKIP i trzy zestawy PowerShell PASS.
Kompilacja Windows WOTC SDK oraz próba v19 w grze: **NIEURUCHOMIONE**.
Kontrole źródeł i helperów nie wykonują natywnego silnika. Pełne logi,
zapisy i dumpy pozostają prywatne.
