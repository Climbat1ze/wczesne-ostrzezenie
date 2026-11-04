# Wczesne Ostrzeżenie

Pulpit sygnałów zagrożenia wobec Polski i Bałtów z ocenionych źródeł RSS, aktualizowany co godzinę. Główny parametr: współczynnik wpierdolu (WW, 0–100) i zegar zagłady.

**Strona:** https://climbat1ze.github.io/wczesne-ostrzezenie/ · **Metodyka:** https://climbat1ze.github.io/wczesne-ostrzezenie/metodyka.html

To prywatne narzędzie, nie komunikat władz. Oficjalne alerty: Rządowe Centrum Bezpieczeństwa (gov.pl/web/rcb) i Alert RCB w telefonie.

## Jak czytać
- **Kolor i indeks 0–100:** ile kategorii wskaźników naraz jest aktywnych wobec Polski i Bałtów, ważone oceną źródła.
- **Spiętrzenie sygnałów:** Uwaga (1 kategoria z 3+ niezależnymi redakcjami w 72 h), Ostrzeżenie (2), Alarm (3, w tym ewakuacja, ostrzeżenia wywiadu, mobilizacja albo zamknięcia nieba). Mail idzie tylko przy wzroście do Ostrzeżenia lub Alarmu.
- **Sygnał krytyczny:** ewakuacja ambasady, mobilizacja, art. 4/5 NATO, zamknięcie nieba albo atak zbrojny wobec Polski lub Bałtów, opisane przez 2 niezależne redakcje A/B w 24 h. Mail od razu.
- **Alarm trendu:** rusza po zebraniu 21 dni historii.
- **Analogia 2021/22:** 10 zdarzeń sprzed ataku na Ukrainę i czy mają dziś odpowiednik wobec flanki.

## Skan na żądanie, weryfikacja linku, kontrola jakości (wersja 2.0)
- **Szukaj teraz** (zakładka SKAN, bez konta): przeglądarka przeszukuje `strona/szukaj.json`, nagłówki z 3 dni ze wszystkich źródeł.
- **Pełny skan albo link** (każdy z kontem GitHub starszym niż 30 dni): formularz issue `skan` → workflow `zgloszenia.yml` → `app/zgloszenia.py`. Plan i analiza na Claude sonnet (2 wywołania na zgłoszenie, bez narzędzi), szukanie w archiwum 7 dni, w kanałach teraz i w Google News z 30 dni, werdykt z pewnością i 3+ hipotezami konkurencyjnymi w komentarzu issue.
- **Historia i analiza wsteczna**: gałąź `zgloszenia`; w poniedziałek ponowne sprawdzenie zgłoszeń sprzed 7 i 30 dni (trafność, wynik Briera, lekcje dla autoulepszania). Zakładki ZGŁOSZENIA i JAKOŚĆ.
- **Kontrola intencji** (`app/intencja.py`): działania strony własnej i sojuszniczej nie liczą się w kategoriach z flagą `tylko_przeciwnik`; model sonnet raz na godzinę może zdjąć kategorię z wpisów, które podnoszą spiętrzenie.
- **Wersje i zmiany**: `app/WERSJA`, `CHANGELOG.md`, rejestr Change Requests `docs/change_requests.md`, formularz issue „Zgłoszenie zmiany”.

## Maile
Mailem przychodzą tylko alarmy (spiętrzenie sygnałów, sygnał krytyczny, alarm trendu) i raport tygodniowy w poniedziałek rano. Odbiorcy są w kopii ukrytej i nie widzą swoich adresów nawzajem. Żeby dopisać lub usunąć odbiorcę, nadpisz sekret pełną listą adresów po przecinku:

```
gh secret set MAIL_DO -R Climbat1ze/wczesne-ostrzezenie
```

## Jak to działa
Workflow `.github/workflows/ostrzezenie.yml` ma w harmonogramie minuty 13 i 43, ale pomija przebieg, gdy dane mają mniej niż 40 minut, więc zwykle działa raz na godzinę, a zgubione przez GitHub uruchomienie nadrabia drugi wpis. Pobiera kanały, tłumaczy bałtyckie nagłówki (Claude haiku na subskrypcji, w ramach dziennego budżetu), liczy WW, wysyła alarmy (najwyżej 3 na dobę, reszta zbiorczo) i publikuje stronę na GitHub Pages. Stan (historia, wpisy, statystyki źródeł, budżet, dziennik maili i alarmów, zdrowie) żyje na gałęzi `dane`, nadpisywanej jednym commitem przy każdym przebiegu.

W poniedziałek rano ten sam przebieg dodatkowo:
- przegląda źródła (martwe kanały, koniec 30 dni próby) i zapisuje `app/zrodla.yaml` na `main`;
- ocenia trafność klasyfikacji na losowej próbce 30 wpisów z tygodnia (Claude haiku);
- przelicza mnożniki wiarygodności źródeł z danych (0,6–1,2, po 30 dniach statystyk);
- czyta oceny właściciela z issue (`ocena-trafny`, `ocena-pomylka`) i dopisuje je do `tests/dane/`;
- wysyła raport administracyjny do `MAIL_ADMIN`: zużycie, przegląd źródeł, zdrowie, jakość, linki do ocen alarmów.

O 8:30 UTC `autoulepszanie.yml` prosi Claude (sonnet) o propozycję poprawek reguł dopasowania i zakłada PR do przeglądu. 1. dnia miesiąca `przeglad-bezpieczenstwa.yml` zakłada issue z przeglądem bezpieczeństwa.

Ręczne uruchomienie: Actions → wczesne-ostrzezenie → Run workflow (opcja „Wyślij raport mailem teraz”; ręczny przebieg zawsze robi też przegląd poniedziałkowy).

## Konfiguracja
| Nazwa | Rodzaj | Do czego |
|---|---|---|
| `SMTP_USER` | sekret | adres Gmail nadawcy |
| `SMTP_PASS` | sekret | hasło aplikacji Gmail (myaccount.google.com/apppasswords) |
| `MAIL_DO` | sekret | odbiorcy po przecinku |
| `CLAUDE_CODE_OAUTH_TOKEN` | sekret | tłumaczenie nagłówków; wynik `claude setup-token`. Bez niego nagłówki zostają w oryginale |
| `MAIL_ADMIN` | sekret, opcjonalny | odbiorca maili o przeglądzie źródeł (domyślnie nadawca) |
| `VIRUSTOTAL_API_KEY` | sekret, opcjonalny | klucz darmowego API VirusTotal do cotygodniowego sprawdzenia domen linków; bez niego sprawdzenie jest pomijane |
| `SITE_URL` | zmienna | adres strony, wstawiany do maili |
| `STATUS_GODZINY` | zmienna, opcjonalna | godzina raportu, czas Warszawy (domyślnie `7`) |
| `STATUS_DNI` | zmienna, opcjonalna | dni raportu, 1 = poniedziałek (domyślnie `1`) |
| `STATUS_FORMA` | zmienna, opcjonalna | `tydzien` (raport tygodniowy, domyślnie) albo `dzien` (pełny skrót) |
| `CLAUDE_BUDZET_DZIENNY` | zmienna, opcjonalna | dzienny limit zapytań do Claude (domyślnie `150`); po wyczerpaniu nagłówki zostają w oryginale, jeden mail do administratora na dobę |
| `CLAUDE_WYLACZ` | zmienna, opcjonalna | `1` = żadnych wywołań Claude (tłumaczenie, oceny, przeglądy) |
| `ZGLOSZENIA_DZIENNIE` | zmienna, opcjonalna | najwyżej tyle skanów na żądanie na dobę razem (domyślnie `10`) |
| `ZGLOSZENIA_NA_OSOBE` | zmienna, opcjonalna | na autora na dobę (domyślnie `3`; właściciel i współpracownicy bez limitu na osobę) |
| `KONTO_MIN_DNI` | zmienna, opcjonalna | minimalny wiek konta GitHub zgłaszającego (domyślnie `30`) |
| `ZGLOSZENIA_WYLACZ` | zmienna, opcjonalna | `1` = skany na żądanie wyłączone (odpowiedź „chwilowo wyłączone”) |
| `ALARMY_DZIENNIE` | zmienna, opcjonalna | najwyżej tyle alarmów mailem na dobę (domyślnie `3`); kolejne czekają w kolejce i idą zbiorczo o godzinie raportu albo z następnym alarmem |

## Jakość i bezpieczeństwo

Czuwanie (`.github/workflows/czuwanie.yml`, co godzinę): gdy dane na gałęzi `dane` mają ponad 90 minut, uruchamia główny workflow ręcznie; po 3 godzinach zakłada issue z etykietą `przerwa` (powiadomienie mailem od GitHuba) i zamyka je samo po powrocie danych.

Linki z kanałów, dwie warstwy (`app/linki.py`):
1. Przy każdym przebiegu, lokalnie: link musi być http/https, bez adresu IP, punycode, danych logowania i niestandardowego portu, z domeny kanału (albo z pola `domeny_linkow` źródła) i spoza `app/linki_blokada.yaml`. Link, który nie przejdzie, zastępuje strona główna redakcji; powód trafia do `dane/linki_odrzucone.jsonl`.
2. W poniedziałek (`.github/workflows/linki-virustotal.yml`): domeny kanałów i linków z 7 dni sprawdzane w VirusTotal (raport domeny, nic nie jest wysyłane do skanowania). Co najmniej 2 silniki „malicious” = automatyczna blokada domeny; 1 silnik albo co najmniej 2 „suspicious” = issue `bezpieczenstwo` do decyzji właściciela.

- **Testy** (`testy.yml`, każdy push i PR): regresja klasyfikacji na zamrożonych prawdziwych nagłówkach (`tests/dane/przypadki.jsonl`; znane pomyłki jako xfail), budżet i limity, zdrowie, samouczenie. Na PR dodatkowo **strażnik** (`app/straznik.py`): zmiana progów, wag lub flag kategorii zatrzymuje PR. Te wartości zmienia tylko właściciel.
- **Zdrowie**: incydent, gdy przez 3 przebiegi z rzędu pobrano mniej niż 80% kanałów albo tłumaczenie zwraca błędy; jeden mail do administratora na incydent.
- **Samouczenie** nie rusza progów ani wag: zmienia tylko mnożnik wiarygodności źródła (0,6–1,2) i dopisuje przypadki testowe z ocen właściciela.
- **Autoulepszanie** proponuje zmiany wyłącznie we wzorcach i wykluczeniach `app/wskazniki.yaml` oraz w `app/zrodla.yaml`; PR zawsze przegląda człowiek. PR założony przez Actions nie uruchamia `testy.yml`: wynik testów jest w opisie PR.
- **Łańcuch dostaw**: akcje przypięte do pełnych SHA, Claude Code i pakiety pip do wersji, Dependabot co tydzień, CodeQL na push i PR.
- **Claude**: zawsze jawny model i `--tools ""` (tłumaczenie, oceny) albo tylko odczyt (przegląd bezpieczeństwa); treść RSS idzie przez stdin, nigdy do powłoki. Budżet `CLAUDE_BUDZET_DZIENNY`, wyłącznik `CLAUDE_WYLACZ=1`.
- **Logi są publiczne**: aplikacja nie wypisuje adresów e-mail ani treści błędów SMTP; przegląd bezpieczeństwa liczy adresy w logach i maskuje je w wyniku.
- **Nowe źródła**: 30 dni próby i 30 dni karencji w sygnałach krytycznych (pole `dodano` w `app/zrodla.yaml`; źródła z rejestru startowego 2026-11-02 są bez karencji).

## Uruchomienie lokalne
```
cd app
pip install -r requirements-dev.txt
python ostrzezenie.py uruchom --bez-powiadomien
cd .. && python -m pytest -q   # testy: regresja klasyfikacji (tests/dane/przypadki.jsonl), koszty, zdrowie
# otwórz ../strona/index.html
```
Źródła: `python ostrzezenie.py zrodla lista` (także `testuj`, `dodaj`, `ocen`, `status`, `przeglad`).
