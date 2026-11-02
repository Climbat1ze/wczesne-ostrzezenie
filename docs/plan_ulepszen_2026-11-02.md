# Zadanie: wdrożenie ulepszeń w Climbat1ze/wczesne-ostrzezenie (4 etapy po kolei)

Prompt do wklejenia w sesję Claude Code. Pracujesz WYŁĄCZNIE w repo Climbat1ze/wczesne-ostrzezenie. Odpowiadasz po polsku, prozą, konkluzja na górze.

## Kontekst (sprawdzony 2026-11-02)
- Aplikacja w Pythonie: `app/ostrzezenie.py` (główna), `app/tlumacz.py` (tłumaczenie przez `claude -p --model haiku --tools ""`, limit `MAKS_ZAPYTAN = 16` na przebieg, `PACZKA = 40`), `app/poczta.py` (Gmail SMTP, odbiorcy w BCC, `MAIL_ADMIN` = odbiorca maili administracyjnych, domyślnie nadawca), `app/utrzymanie.py` (cotygodniowy przegląd źródeł według reguł), `app/wskazniki.yaml` (kategorie, wagi, reguły dopasowania), `app/zrodla.yaml` (źródła z oceną A–F), `app/strona.py` (budowa strony, tekst przez `html.escape`).
- Workflow `.github/workflows/ostrzezenie.yml`: cron `47 * * * *`, ręczne uruchomienie z opcją `mail_skrot`. Stan żyje na gałęzi `dane` (nadpisywanej jednym commitem przy każdym przebiegu). Rejestr źródeł po przeglądzie trafia na `main`.
- Sekrety: SMTP_USER, SMTP_PASS, MAIL_DO, CLAUDE_CODE_OAUTH_TOKEN, opcjonalnie MAIL_ADMIN. Zmienne: SITE_URL, STATUS_GODZINY, STATUS_DNI, STATUS_FORMA.
- Repo jest publiczne: logi Actions widzi każdy. Nigdy nie wypisuj w logach adresów e-mail ani treści sekretów.
- Powiadomień ntfy NIE wdrażaj (właściciel odłożył tę funkcję).

## Zasady pracy
1. Każdy etap = osobna gałąź i osobny pull request. Gałąź etapu N wychodzi z gałęzi etapu N−1 (stos), bo etapy zależą od siebie. Niczego nie scalaj do `main` sam.
2. Przed każdym PR uruchom lokalnie testy (`pytest`) i jedno uruchomienie aplikacji: `python app/ostrzezenie.py uruchom --bez-powiadomien`. W opisie PR wklej wynik.
3. Nie proś o wartości sekretów w czacie. Jeśli etap wymaga nowego sekretu albo zmiennej, wypisz polecenie `gh secret set ...` / `gh variable set ...`, które właściciel wpisze sam.
4. Wywołania Claude w kodzie zawsze z `--tools ""` i jawnym `--model`. Treść z RSS traktuj jako niezaufaną: nigdy nie wstawiaj jej do poleceń powłoki.
5. Nie zmieniaj progów alarmów ani wag kategorii w `wskazniki.yaml`. To decyzja właściciela.
6. Commit messages: `[typ] YYYY-MM-DD opis`. Opis PR kończ linią: 🤖 Generated with Claude Code.
7. Po każdym etapie napisz w czacie 3–5 zdań: co zmieniłeś, w których plikach, jak to sprawdziłeś, link do PR. Potem przejdź do kolejnego etapu bez czekania, chyba że testy nie przechodzą — wtedy zatrzymaj się i opisz błąd.

## Etap 1: bezpieczeństwo i blokady kosztów (gałąź `etap1-bezpieczenstwo-koszty`)
Bezpieczeństwo:
1. W workflow przypnij `@anthropic-ai/claude-code` do konkretnej aktualnej wersji (sprawdź `npm view @anthropic-ai/claude-code version`).
2. Przypnij akcje GitHuba do pełnych SHA commitów z komentarzem z wersją (`uses: actions/checkout@<sha> # v4.x.x`). Przy okazji przejdź na wersje działające na Node.js 24, jeśli istnieją.
3. Przypnij wersje w `app/requirements.txt` (`==`).
4. Dodaj `.github/dependabot.yml`: ekosystemy `github-actions`, `pip` (katalog `/app`), interwał tygodniowy.
5. Dodaj workflow CodeQL dla Pythona (push na `main` i PR).
6. W `ostrzezenie.py`: źródło dodane do `zrodla.yaml` w ostatnich 30 dniach nie liczy się do sygnału krytycznego (jeśli brak daty dodania w rejestrze, dodaj pole `dodano` i uzupełnij istniejące źródła datą 2026-11-02).
7. Dodaj comiesięczny workflow `przeglad-bezpieczenstwa.yml` (cron 1. dnia miesiąca): Claude (`claude -p`, model sonnet, `--tools "Read,Grep,Glob"`) przegląda workflow, zależności i ostatnie logi pod kątem wycieku adresów oraz ryzyk łańcucha dostaw. Wynik zakłada jako issue z etykietą `bezpieczenstwo`.
8. Wypisz właścicielowi polecenie do włączenia alertów Dependabota: `gh api -X PUT repos/Climbat1ze/wczesne-ostrzezenie/vulnerability-alerts`.

Blokady kosztów:
1. Dzienny budżet zapytań do Claude: licznik w `app/dane/budzet.json` (data + liczba wywołań), domyślnie 150 na dobę, nadpisywalny zmienną `CLAUDE_BUDZET_DZIENNY`. Po wyczerpaniu: nagłówki zostają w oryginale, jeden mail do MAIL_ADMIN na dobę.
2. Wyłącznik awaryjny: zmienna `CLAUDE_WYLACZ=1` pomija wszystkie wywołania Claude (tłumaczenie, oceny, przeglądy).
3. Limit maili: najwyżej 3 alarmy na dobę do MAIL_DO. Kolejne sklejaj w jeden zbiorczy mail o najbliższej pełnej godzinie raportu albo dołączaj do następnego alarmu.
4. Raport zużycia w poniedziałkowym mailu: liczba wywołań Claude, liczba wysłanych maili, czas przebiegów (z `GITHUB_RUN_*` / pomiar w kodzie) za ostatnie 7 dni.
5. Dopisz nowe zmienne do tabeli w README.

## Etap 2: kontrola jakości (gałąź `etap2-kontrola-jakosci`, z etapu 1)
1. Zdrowie przebiegu: po każdym przebiegu zapisz do `app/dane/zdrowie.json` liczbę pobranych kanałów, błędy tłumaczenia, czas odświeżenia `strona/dane.json`. Mail do MAIL_ADMIN, gdy przez 3 kolejne przebiegi pobrano mniej niż 80% aktywnych kanałów albo tłumaczenie zwraca błędy. Jeden mail na incydent, nie co godzinę.
2. Testy regresji: katalog `tests/`, zestaw ok. 50 prawdziwych wpisów z `app/dane/wpisy.jsonl` zamrożonych w `tests/dane/` z oczekiwaną kategorią, udziałem w WW i poziomem alarmu (wygeneruj z obecnego zachowania, oznacz wyraźnie wpisy oczywiście błędne, np. nagłówki sportowe, jako „znana pomyłka”). Workflow `testy.yml` na push i PR.
3. Ocena trafności (poniedziałek, w ramach istniejącego przebiegu z przeglądem źródeł): losowa próbka 30 wpisów z 7 dni, Claude (haiku, `--tools ""`) ocenia każdy: czy dotyczy Polski/Bałtów, czy kategoria pasuje. Odsetek trafnych do `app/dane/jakosc.jsonl` i do poniedziałkowego maila (tylko do MAIL_ADMIN). Wywołania liczą się do budżetu z etapu 1.

## Etap 3: samouczenie się (gałąź `etap3-samouczenie`, z etapu 2)
1. Wiarygodność źródeł z danych: źródło, którego trafienia inne redakcje potwierdzają w 72 h, zyskuje; alarmujące samotnie traci. Zmiana najwyżej o 1 klasę na miesiąc, tylko po 30 dniach statystyk. Każda zmiana do `app/dane/dziennik_uczenia.jsonl` (co, z jakiej na jaką, dlaczego).
2. Poziom bazowy osobno dla każdej kategorii i każdego dnia tygodnia (zamiast samej średniej 30 dni) do wykrywania nagłego skoku.
3. Oceny właściciela: w poniedziałkowym mailu przy każdym alarmie z tygodnia dwa linki „trafny” / „pomyłka” otwierające gotowe issue (`/issues/new?title=...&labels=ocena-trafny|ocena-pomylka&body=<id wpisu>`). Przebieg poniedziałkowy czyta zamknięte i otwarte issue z tymi etykietami (`GITHUB_TOKEN`, uprawnienie `issues: read`) i dopisuje je do `tests/dane/` jako nowe przypadki.
4. Samouczenie NIE zmienia progów alarmów ani wag kategorii.

## Etap 4: autoulepszanie (gałąź `etap4-autoulepszanie`, z etapu 3)
1. Workflow `autoulepszanie.yml`, poniedziałek po głównym przebiegu (np. cron `30 8 * * 1`), `timeout-minutes: 20`.
2. Claude Code (sonnet, `--max-turns 30`, narzędzia ograniczone do Read/Edit/Grep/Glob/Bash(pytest)) czyta: ostatni wynik z `jakosc.jsonl`, wpisy ocenione jako pomyłki, issue `ocena-pomylka`, statystyki źródeł.
3. Proponuje zmiany TYLKO w regułach dopasowania (`wskazniki.yaml`, np. wykluczenia) i w `zrodla.yaml`. Progi i wagi poza zakresem — workflow ma odrzucić PR, jeśli diff je zmienia (prosty test w `testy.yml`).
4. Otwiera PR z uzasadnieniem każdej zmiany i wynikiem testów regresji przed i po. Nigdy nie scala sam. Wywołania liczą się do budżetu z etapu 1; przy `CLAUDE_WYLACZ=1` job kończy się bez działania.
5. Uprawnienia joba: `contents: write`, `pull-requests: write`, nic więcej.

## Na koniec
1. Zaktualizuj README (sekcje: Jak to działa, Konfiguracja, nowa sekcja Jakość i bezpieczeństwo) w gałęzi etapu 4.
2. Podsumuj w czacie: lista 4 PR z linkami, kolejność scalania (1 → 2 → 3 → 4), polecenia `gh secret set` / `gh variable set` / `gh api`, które właściciel musi wpisać sam, i co sprawdzić po scaleniu (ręczne uruchomienie workflow, które linie logu).

Liczby (budżet 150/dobę, 3 alarmy/dobę, próbka 30, próg 80% przez 3 przebiegi, karencja 30 dni) to propozycje projektowe, nie pomiary. Zmień przed uruchomieniem, jeśli trzeba.
