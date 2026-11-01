# Profil zgodności i stan weryfikacji

## Docelowa instalacja

Profil wskazany przez użytkownika to [XCOM 2 Collection ze Steam](https://store.steampowered.com/bundle/7118/XCOM_2_Collection/), aktualna wersja na Windows, oficjalne dodatki i **wyłącznie mod Autoplay XCOM 2**.

Grę należy uruchamiać jako **War of the Chosen**. Collection jest zestawem produktów Steam, a nie osobnym silnikiem ani zamiennikiem trybu WOTC. Mod nie jest przeznaczony do uruchomienia w podstawowym XCOM 2 bez WOTC. Nie wymaga Highlandera, Long War, Mod Config Menu ani innych modów. AML jest opcjonalnym programem uruchamiającym, nie modem wymaganym przez kod.

Nie przypisujemy konkretnego numeru builda Steam ani nie traktujemy listy klas SDK jako potwierdzenia aktualnej oferty sklepu. Odczyt wskazanej strony Steam z tego środowiska został odrzucony przez proxy (HTTP CONNECT 403); profil produktu pochodzi z wymagania użytkownika. Nie próbowano omijać tej blokady.

## Co sprawdzono w rzeczywistej paczce

Załączony `AutoplayXCom2.zip` zawiera własny skompilowany pakiet, trzy pliki INI, manifest WOTC, lokalizacje PL/EN w UTF-16LE z BOM i instrukcję. Konfiguracja oraz teksty odpowiadają repozytorium. Zachowano 27 nazw zdolności i poprawny `DLCIdentifier`.

Odczytano binarne tabele pakietu `.u` bez uruchamiania go. Wszystkie 464 importy prowadzą do trzech standardowych pakietów: `Core` (30), `Engine` (41), `XComGame` (393). Są wszystkie dziewięć klas moda. Nie ma zależności od pakietów innych modów, w tym Highlandera/CH, Long War czy Mod Config Menu. Sprawdzono też natywny mechanizm `UIScreenListener` w oryginalnym SDK i oficjalnym DLC_3.

Format pliku to UE3 845 / licensee 120, z polem wersji silnika 8917. **Te liczby nie są numerem builda Steam.** Kompilacja zakończyła się zerem błędów; pozostało osiem ostrzeżeń SDK, bez odrzucanych ustawień moda.

Oryginalny `.u` ma 285 057 bajtów i SHA-256:

```text
14e50b050e38b198f85f0b0575e8661382d838f148e924eb217847bfbb79d802
```

Przy przygotowaniu paczki instalacyjnej ten plik i pliki konfiguracji pozostają niezmienione. Zaktualizowano instrukcję oraz dodano informację o wydaniu.

## Czego te sprawdzenia nie potwierdzają

Nie uruchomiono gry w tym środowisku. Nie potwierdzono na najnowszym runtime Steam wyświetlania HUD, odczytu INI i wykonywania akcji, ani ukończenia każdej misji DLC. Brak zależności od innych modów i poprawna kompilacja nie stanowią takiego testu.

Pierwsza próba powinna odbyć się na czystym WOTC z tym jednym modem i osobnym zapisem. Wymagane próby są w [TESTING.pl.md](TESTING.pl.md); znane ograniczenia planera i misji opisuje [README](../README.md). W razie problemu potrzebny jest `Launch.log` z tej próby oraz informacja o rodzaju misji i widocznym statusie autoplaya.
