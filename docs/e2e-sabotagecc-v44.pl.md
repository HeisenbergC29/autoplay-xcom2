# Od decyzji o ruchu do podłożenia X4 w SabotageCC

Próba sprawdza awaryjne dojście do X4 na Windows w XCOM 2 WOTC. W v45 autoplay zatrzymał się w turach 19–20 mimo rozpoznania punktu interakcji X4. Po ręcznych ruchach żołnierza 415 misja zakończyła się zwycięstwem w turze 29. [Raport v45](report-v45-2026-11-21.pl.md)

1. Zbuduj paczkę v48 z [próby #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4). Użyj tego samego poziomu trudności i zapisu SabotageCC sprzed zastoju, jeśli go masz. W przeciwnym razie rozpocznij osobny przebieg. Sprawdź `revision=mission-report-v48` w nagłówku sesji.
2. Włącz autoplay. W próbie autonomicznej pozostaw ruch, interakcję X4 i ponowne planowanie automatowi. Interesujące okno to żołnierz z dwoma zwykłymi AP i zdolnością podłożenia X4, gdy cała drużyna wyczerpała zwykłe konstruktywne propozycje. W v45 wystąpiło w turach 19–20. Jeżeli drużyna dojdzie zwykłą trasą, zapisz wynik misji i oznacz awaryjne dojście jako **brak okazji do testu**.
3. Odczytaj kolejne decyzje tej samej sesji. Przy `objective_recovery_scan` sprawdź `found` i `reason`. Przy `objective_recovery_candidate` porównaj jednostkę i pole końcowe z `chosen` o `kind=move`, `move_planner=objective_recovery` i `accepted=True`. Potwierdź wynik `StandardMove` i pozycję po ruchu. Odrzucone kandydatury można odróżnić po braku zgodnego zaakceptowanego rozkazu. Jeśli żadna droga nie przejdzie oceny, zachowaj powód zatrzymania i stan celu. Kolejne identyczne zatrzymania przy tych samych AP mają znaczenie diagnostyczne.
4. Śledź kolejne decyzje aż do zdarzenia podłożenia albo końca misji. Jeśli dojście do X4 wymaga kilku ruchów, sprawdź także ostatni z nich. Szukaj w odświeżonym jawnym wykazie zdolności `Interact_PlantBomb`, `code=AA_Success` i co najmniej jednego celu. Następnie sprawdź `chosen` z zaakceptowanym `Interact_PlantBomb`, natywny `result` oraz ukończenie celu w grze. Sam wynik interakcji może też pochodzić z fazy ręcznej. Zapisz każdą interwencję gracza.
5. Zachowaj raport przed ponownym uruchomieniem gry. Podaj trzy oddzielne wyniki: wykonanie ruchu awaryjnego, automatyczne ukończenie X4 oraz wynik misji. Do zaliczenia całej próby wymagane są samodzielne zwycięstwo i potwierdzony końcowy wynik bieżącej misji powyżej zera. Przy braku ostatecznej punktacji sukces interakcji nadal można zweryfikować. Zgodnie z ustaleniem użytkownika przy 0 błędów i 0 ostrzeżeń wystarczy podać wynik kompilacji bez logu.

Automatyczny test raportowania uruchamia rzeczywiste polecenie analizatora dla syntetycznego ZIP-a z dwiema sesjami. Sprawdza przyjęty ruch i interakcję w jednej sesji oraz odrzucony ruch i ręczną interakcję w drugiej. Osobny syntetyczny log v46 sprawdza przyjęty objazd oraz zachowanie wyniku po przejściu do menu. Polecenie do odtworzenia testu:

```sh
python -m unittest discover -s tests -p test_sabotagecc_report_e2e_v44.py
```

Wykonanie rozkazów w silniku, legalność konkretnej ścieżki i ocena kandydata przez natywny planer wymagają przebiegu opisanego w krokach 1–5.
