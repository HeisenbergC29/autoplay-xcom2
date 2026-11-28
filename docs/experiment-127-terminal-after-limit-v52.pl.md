# #127 — zakończenie sesji po limicie detali

Baza `411c8d4828be6315b750231967a959da884381ef`, gałąź
`helper/127-terminal-after-record-limit`. Jedno niezależne zadanie.
Roboczy marker runtime v52 (PR #134 ma v51); przed wspólną paczką LEAD
uzgadnia końcowe markery Recorder/UI/DLC i ich testy.

## Dowód

LEAD w #127 wskazał dwie sesje v46 (Rescue Shen i Rescue Jane Kelly)
z `limit` seq20001, bez `end`. Ponownie zweryfikowany prywatny ZIP v50
z 27 XI (CRC PASS) zawiera 112648 rekordów, w tym:

| Sesja | Misja | Limit | End |
| --- | --- | --- | --- |
| 2026-11-27_16-51-38-357_6819 | LostAndAbandonedB | seq20001, D113 | brak |
| 2026-11-27_18-49-12-600_6819 | LostAndAbandonedC | seq20001, D132 | brak |

To dowód ucięcia obserwacji, nie dowód porażki ani przyczyny zatrzymania gry.
Nie publikujemy logów. Osobny limit analizatora 100000 rekordów w całym
wejściu jest zachowany. Rozbicie większego ZIP lub zmiana jego limitu nie
należą do tego PR.

## Kontrakt

- `Emit` zachowuje limit Clamp(MaxRecords,100,100000) dla zwykłych
  rekordów oraz jeden komunikat limit. Jedyny wyjątek, wyłącznie w Finish,
  to końcowy `end` albo `recording_context_lost`. Po zamknięciu nie ma
  żadnego następnego wpisu. Maksymalna liczba to limit detali + 2.
  Nie zwiększamy limitu, nie odblokowujemy score_delta/game_score, nie
  rejestrujemy wielokrotnie oczekiwania na winner po cap.
- `IsRecordingMission` sprawdza istniejący kontrakt instancji historii,
  start index, brak rewind, ID i typ bitwy także po cap. Zwykli obserwatorzy
  nadal nie czytają detali; tylko Finish może dopuścić terminalny odczyt.
  Brak bitwy lub niewłaściwy epoch daje recording_context_lost, nie end
  z nowej misji. Flaga bRecordingEpochInvalid nadal zatrzaskuje mismatch.
- `Finish` czeka na natywny VictoriousPlayer przy tactical_game_ended,
  zachowuje unknown gdy nie ma rozstrzygnięcia przy zwykłym zamykaniu,
  emituje raz i zwalnia obserwatory. Nie wnioskuje win/loss z punktów.
  Jeżeli kontekst utracono, nie odczytuje wyniku nowej bitwy.
- Cursor odzwierciedla ostatnią zakończoną ramkę skanowania: gdy limit
  odrzuci detail wewnątrz ramki w RecordResults, cofamy cursor o tę
  niedokończoną ramkę. Nie powtarzamy jej po cap. `history_pending` pozostaje
  różnicą aktualnego indeksu i kursora; nawet przy zero nie oznacza pełnej
  obserwacji po cap. Nowe pole `details_truncated` jest jawne.
- W analizatorze limit (także stary format) lub details_truncated wskazują
  brak kompletności; zachowujemy natywny outcome z end, oddzielnie
  potwierdzenie punktacji. W szczególności nie certyfikujemy finalnego
  Legacy game_score ani Challenge CMPT_TotalScore przy cap, nawet gdy
  podano history_pending=0 lub mission_final=true. Zachowujemy osobne
  źródła i dotychczasowe bramki końcowych punktów. Stary cap bez end i
  context_lost pozostają outcome unknown; win bez pełnych punktów nie
  zalicza próby, loss pozostaje fail. Zwykły nieobcięty wynik nie zmienia
  semantyki. Diagnostyka i analiza patrolu również jawnie niepełne.

## Weryfikacja

`tests/test_recorder_terminal_limit_v52.py`: test-only translator wykonuje
rzeczywiste metody UC Emit, RecordingEpochMatches, IsRecordingMission i
Finish z kontrolowanymi fixture SDK. Sprawdza mały skonfigurowany limit
(realny clamp 100), powtarzane Finish, winner pending, zmianę epoch,
rewind, brak bitwy, zwykłe zamknięcie i kontrakt kursora/score. E2E używa
prawdziwego CLI na syntetycznym ZIP z sesjami capped Legacy, capped
Challenge, samą flagą, zdrową sesją, loss, context_lost i starym cap bez
end. Mock nie zastępuje WOTC. Nie zmieniono natywnych API odczytu historii
i winner; istniejące prywatne kontrakty SDK dotyczą tych samych pól.

## Próba Windows po review

LEAD wyznacza jedną zintegrowaną paczkę. Do diagnostycznej próby ustawić
MaxRecords=100 (clamp 100), rozegrać lub pozwolić AI ukończyć misję.
Oczekujemy seq101 limit, seq102 end (jeśli nie utracono kontekstu);
end z rzeczywistym winner i details_truncated=True, właściwe pending.
Jeżeli kontekst zmieni się przed rozstrzygnięciem, zamiast end oczekujemy
recording_context_lost. Po kilku tickach/Destroy brak drugiego end.
Przywrócić normalny MaxRecords. Druga zwykła próba nieobcięta sprawdza
utrzymanie finalnego native score. Nie jest to dowód poprawy taktyki.
Windows build i gameplay NOT RUN. Pełny lokalny audit SDK/checkout
nieprzeprowadzony: środowisko kontenera nie rozwiązuje github.com.
