# Wybór między strzałem, flanką i Overwatch po ujawnieniu drużyny

Eksperyment #104 rozwija taktykę strzelców po rozpoczęciu walki. Bazą jest v44 z PR #102, commit `8716a3b478de16f19519086cd4dd6437e8553fac`. Nowe raporty rozpoznaje się po `revision=mission-report-v45`. Kompilacja v45 w Windows WOTC SDK i próba w grze czekają na użytkownika.

## Co wydarzyło się w v43

W pierwszej turze GasStation (`ChallengeAbductionGasStation`) autoplay podjął pięć kolejnych decyzji.

| Decyzja | Rozkaz | Wynik z historii gry |
| --- | --- | --- |
| D1 | Medyk 63468 przeszedł na (18,22,1). Ocena ruchu 80, szacowana ekspozycja 77,5055 → 3,6907 | Gra przyjęła ruch, `offensive_forecast=False` |
| D2 | Snajper 63480 wykonał `SniperStandardFire` do 63502. Szansa 82%, ocena 55,08 | Trafienie, 10 → 5 HP |
| D3 | Żołnierz 63474 wykonał `StandardShot` do 63502. Szansa 71%, ocena 88,08 | Pudło, 5 → 5 HP |
| D4 | Żołnierz 63486 wykonał `StandardShot` do 63502. Szansa 70%, ocena 87,17 | Trafienie, eliminacja 63502 |
| D5 | Medyk 63468 wykonał `StandardShot` do 63501. Szansa 85%, ocena 49,60 | Trafienie, 10 → 7 HP |

`PoisonSpit` Vipera zatruł trzech żołnierzy pozostających blisko siebie. Odtworzenie kolejności pokazuje, dlaczego warto badać pozycje i akcje sprzed naliczenia kary. Sam raport nie rozstrzyga, czy w tych decyzjach istniała legalna flanka o mniejszym ryzyku lub wyższej wartości.

W całej GasStation po 12 rozkazach włączenia Overwatch wystąpiły trzy strzały reakcyjne, wszystkie w turze 8. Żołnierz 63474 spudłował z szansą 41% do 63506. Żołnierz 63486 trafił ten sam cel przy 61%. Medyk 63468 spudłował do 63504 przy 55%. Te obserwacje nie wyznaczają prawdopodobieństwa przyszłej reakcji. W trzech sesjach v43 nie odnotowano wybranego ruchu z `offensive_forecast=True`.

W SabotageCC żołnierz 422 wciąż strzelał po stronie gracza w D114. W D115 pozycja `seq=11719` pokazuje go już jako `visible_enemy`. Dopiero w D116 jednostka 416 ponownie uzbroiła Overwatch (`seq=11846`). Strzał reakcyjny 416 do 422 chybił przy 52% (`history=4014`), a 422 trafił 416 przy 81% (`history=4024`). Zmiana strony była więc widoczna przed drugim uzbrojeniem. APXREC oznaczył wcześniejszy atak jako `unseen_attack`, bez identyfikacji jego wykonawcy. W 22. turze tej sesji były również ruchy ręczne.

Źródłem obserwacji jest bieżący `Logs/Launch.log` z prywatnej paczki `AutoplayXCom2-20261115-014717-48d33941.zip`. [Bilans prób v43](report-v43-2026-11-15.pl.md)

## Jak v45 ocenia flankę

Planer porównuje aktualnie legalne akcje drużyny. Dobry strzał może zostać wykonany od razu. Ruch ofensywny konkuruje z nim pod warunkiem, że ujawniony żołnierz ma dwa punkty akcji, legalny bieżący `StandardShot` lub `PistolStandardShot` i odpowiedni zapas AP po niebieskim ruchu. Prognoza uwzględnia m.in. natywną widoczność z rozważanego pola, osłonę względem celu, odległość i przewagę wysokości. Wymaga poprawy szansy o co najmniej 12 punktów procentowych i wartości ataku o co najmniej 8. Model ma ograniczony zakres. Na przykład D2 w GasStation to `SniperStandardFire`, poza zakresem prognozy.

W v43 test zagrożeń na ścieżce już obejmował pola pośrednie, ale porównanie ekspozycji z pozycją początkową dotyczyło tylko końca trasy. W v45 funkcja `ForecastBluePathSafe` sprawdza każdy krok natywnej ścieżki od bieżącej pozycji do wybranego pola. Kontroluje zagrożenia terenowe, znajomość pola, wsparcie drużyny, ryzyko wybuchowej osłony i szacowaną ekspozycję. Przy wyłączonym Full Intel sprawdza też widoczność pola dla drużyny. Wzrost ekspozycji na dowolnym kroku odrzuca propozycję również wtedy, gdy pole końcowe jest bezpieczne.

Wartości zagrożeń dotyczą bieżącego stanu. Każde sprawdzenie wybuchowej osłony korzysta ze wspólnego limitu na decyzję. Wykonane sprawdzenia pozostają rozliczone po odrzuceniu dalszego kroku. Wyczerpanie limitu oznacza, że kolejnej ścieżki nie udało się w pełni zweryfikować. Nowy strzał po ruchu wymaga świeżych danych o dostępnych akcjach i celach, sprawdzanych z rzeczywistej pozycji.

### Jak czytać raport

`marker|kind=offensive_reposition_scan` opisuje etap oceny jednego żołnierza. Planer bada ograniczoną próbkę do 64 wskazań pól. `supported_native_shots` liczy obsługiwane bieżące pary zdolność–cel. `material_previews` liczy rozpatrzone pola z wystarczającą poprawą. `safe_native_paths` liczy ścieżki, dla których sprawdzono pełną trasę po poprawieniu lokalnej oceny. Pominięte pola i ścieżki nie mają ustalonej oceny bezpieczeństwa.

| Wartość `reason` | Znaczenie w chwili oceny |
| --- | --- |
| `not_ready_for_forecast` | Żołnierz nie spełnia wstępnych warunków modelu |
| `no_supported_current_shot` | Brak obsługiwanej pary aktualnie legalny strzał–cel |
| `native_reachable_cache_missing` | Brak danych gry o osiągalnych polach |
| `no_native_blue_endpoints` | W sprawdzonej próbce brak pola innego niż początkowe z natywnym kosztem osiągalnym niebieskim ruchem |
| `no_material_projected_shot` | Żadne z badanych pól nie przeszło wszystkich filtrów do uzyskania wystarczającej prognozy. Możliwą przyczyną jest także wcześniejszy filtr terenu, wysokości, wsparcia lub ekspozycji |
| `unsafe_or_unverified_blue_path` | Wystąpiła dostateczna prognoza, lecz brak pełnej zaakceptowanej ścieżki. Obejmuje m.in. brak ścieżki, zagrożenie i brak budżetu |
| `nonpositive_move_and_shot_score` | Najlepsza w pełni sprawdzona lokalna propozycja uzyskała ocenę równą zero lub niższą |
| `outscored_by_current_squad_action` | W chwili porównania ocena tej propozycji nie przewyższyła najlepszego dotąd działania |
| `destination_already_visited` | Propozycja przewyższyła najlepszą dotąd ocenę, ale kontroler odrzucił ją z powodu wcześniejszego odwiedzenia pola |
| `safe_move_and_shot_candidate` | Planer zgłosił ruch mogący poprawić późniejszy strzał. Przy dalszym porównaniu drużyna może wybrać inne działanie |

`proposed=True` dotyczy zgłoszenia planera. Dopiero `chosen|kind=move|accepted=True|move_planner=offensive_reposition` wskazuje przyjęty przez grę ruch tego planera. Recorder osobno przelicza prognozę dla celu **każdego** ruchu. Dlatego możliwe jest np. `move_planner=mission` z `offensive_forecast=True`. Pola `native_chance_now` i `projected_chance` w takim zapisie oznaczają odpowiednio obecną szansę oraz oszacowanie przed ruchem. Szansę rzeczywistego nowego strzału odczytuje się później z `chosen|kind=action` i rozstrzygniętego `result` dla tej jednostki i celu.

### Overwatch i odzyskiwalny sojusznik

Do włączenia Overwatch mod porównuje ocenę rezerwacji punktu akcji z ocenami dostępnych działań. Przed porównaniem jednostek kontroler sprawdza wspólną dla drużyny listę żywych wrogów aktualnie widocznych dla gracza. Jeżeli widoczny przeciwnik jest odzyskiwalnym żołnierzem wcześniej należącym do gracza, mod odrzuca nowe Overwatch. Ta sama decyzja obowiązuje przy zwykłym wyborze akcji, przygotowaniu zasadzki patrolowej i zasadzki z ukrycia oraz w końcowym sprawdzeniu dostępności. Zwykły ruch przygotowujący zasadzkę z ukrycia pozostaje dostępny. Brak prawidłowego obserwatora lub przekroczenie limitu 64 widocznych wrogów także wyklucza uzbrojenie. Cel i rzut już uzbrojonej reakcji wybiera gra. Przejęcie żołnierza dopiero po uzbrojeniu pozostaje odrębnym przypadkiem. Dobór liczby strzelców na Overwatch wynika z dostępnych działań drużyny i ich ocen.

## Co sprawdzają testy

Testy jednostkowe wykonują czyste funkcje UnrealScript dotyczące progów ryzyka i oceny strzałów. Testy źródłowe kontrolują użycie natywnych danych o AP, celach, widoczności i ścieżkach. Uruchomienie tych testów nie wykonuje kodu silnika.

Cztery testy CLI uruchamiają `tools/analyze-mission-log.py` na syntetycznych paczkach ZIP. Obejmują sześć osobnych sesji.

- Bezpośredni strzał 82%, trafienie oraz końcowe 120 punktów odnotowane na tym samym indeksie historii co zwycięstwo dają wynik `pass`. W drugiej wersji tego przebiegu ten sam dodatni odczyt pochodzi z wcześniejszego momentu. Zwycięstwo pozostaje potwierdzone, a końcowa punktacja i werdykt pozostają nieznane.
- Ruch od planera ofensywnego zużywa według migawek 2 → 1 AP. Prognoza szansy poprawia się z 35% do 70%. Po ruchu gra w przykładowym zapisie udostępnia strzał z szansą 64%, który chybia. Misja kończy się porażką.
- Dwa odrzucenia ruchu oraz jedno uzbrojenie Overwatch pozostawiają zero zaobserwowanych strzałów reakcyjnych.
- W jednej z dwóch sesji wspólnej paczki po ruchu występują ręczna faza i strzał bez rozkazu autoplay. Automatowi przypisany jest jeden ruch. Dodatni werdykt punktowy ocenia wynik misji. Faza ręczna wymaga osobnej adnotacji o udziale gracza.
- Druga sesja urywa się po przyjęciu ruchu planera misji. Zachowuje korzystną prognozę strzału bez późniejszego rzutu, wyniku końcowego ani potwierdzonej punktacji.

## Co sprawdzić w Windows WOTC

1. Zbudować wskazany przez LEAD commit. Przy wyniku 0 błędów i 0 ostrzeżeń wystarczy potwierdzenie. Przy problemie dołączyć log kompilacji.
2. Uruchomić GasStation i zachować raport z rewizją v45. Porównać wybrane strzały i ruchy z markerami dla tych samych jednostek i decyzji. Szczególnie wartościowy jest przypadek, w którym środkowe pole lub budżet zatrzymały propozycję.
3. Dla przyjętego ruchu `move_planner=offensive_reposition` sprawdzić rzeczywiste AP przed i po ruchu oraz czy późniejszy strzał otrzymał `AA_Success`. Zadeklarowaną szansę i efekt strzału odczytać dopiero po jego wybraniu.
4. Przy powtórzeniu podobnej sytuacji w SabotageCC zestawić status i stronę odzyskiwalnego sojusznika z chwilą uzbrojenia Overwatch. Osobno policzyć rozkazy rezerwy, reakcje i trafienia.
5. Odnotować natywny wynik misji, źródło i kompletność końcowej punktacji oraz ewentualne interwencje gracza. Kryterium projektu to zwycięstwo i potwierdzony dodatni wynik.
