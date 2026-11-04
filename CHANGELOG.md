# Historia zmian

Format: [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/), wersje według [Semantic Versioning](https://semver.org/lang/pl/).
Zasada numeracji w tej aplikacji: **MAJOR** = nowy moduł albo zmiana sposobu liczenia WW, **MINOR** = nowa funkcja bez zmiany
liczenia, **PATCH** = poprawka wzorca, tekstu albo błędu. Wersja żyje w `app/WERSJA`; test `tests/test_wersja.py` pilnuje,
żeby pierwsza pozycja tego pliku była równa wersji. Zgłoszenia zmian (CR): `docs/change_requests.md`.

## [2.0.0] - 2026-11-04

Zgłoszenia zmian: CR-001 do CR-008.

### Dodane
- **Skan na żądanie** (CR-003): zakładka SKAN na pulpicie. „Szukaj teraz” przeszukuje w przeglądarce nagłówki z 3 dni
  (`strona/szukaj.json`, bez konta i bez modelu). „Zleć pełny skan” otwiera formularz issue `skan`; workflow
  `zgloszenia.yml` pobiera wszystkie kanały, szuka w archiwum 7 dni i w Google News z 30 dni, ocenia źródła i odpisuje
  werdyktem z pewnością. Dla każdego użytkownika z kontem GitHub, limit 3 na osobę i 10 razem na dobę.
- **Weryfikacja linku** (CR-004): ten sam formularz z polem Link. Kontrola adresu (reguły linków + blokada adresów
  prywatnych i przekierowań na nie), pobranie strony do 2 MB, ocena domeny z rejestru, szukanie innych wystąpień.
- **Kontrola strony i intencji** (CR-005, `app/intencja.py`): reguła „pierwszy aktor + czasownik” (strona własna nie liczy
  się w kategoriach z flagą `tylko_przeciwnik`: koncentracja wojsk, gotowość i mobilizacja, ćwiczenia przeciwnika) oraz
  model sonnet raz na godzinę dla wpisów, które mogą podnieść spiętrzenie (zdejmuje kategorię przy pewności >= 0,7,
  nie dodaje kategorii, nie wycisza sygnałów krytycznych). Analiza zgłoszeń metodą hipotez konkurencyjnych (min. 3).
- **Historia zgłoszeń i analiza wsteczna** (CR-006): gałąź `zgloszenia` (zwykłe commity = ślad audytowy), zakładki
  ZGŁOSZENIA i JAKOŚĆ, ponowne sprawdzenie po 7 i 30 dniach, trafność werdyktów, wynik Briera, lekcje dla autoulepszania.
- **Wersjonowanie** (CR-002): `app/WERSJA`, wersja w stopce strony, w `dane.json`, w raporcie administracyjnym,
  w odpowiedziach na zgłoszenia i w nagłówku User-Agent.
- **Historia zmian i Change Requests** (CR-001): ten plik, rejestr `docs/change_requests.md`, formularz issue
  „Zgłoszenie zmiany (Change Request)”.
- **Analogia 2021/22 sprawdzana sensem** (CR-007): każdy kamień milowy ma kryterium odpowiednika (kto działa, wobec kogo);
  model sonnet sprawdza każdą parę kamień–wiadomość, liczą się tylko potwierdzone (pewność >= 0,6). Na danych z 4.11:
  8 z 10 → 2 z 10 (odrzucone m.in. rosyjskie oskarżenia Polski jako „ostrzeżenie wywiadu” i europejskie ćwiczenia w Polsce
  jako „ćwiczenia Rosji”). Pulpit pokazuje, ile wiadomości model odrzucił i dlaczego przykład pasuje.
- **Dotłumaczanie zaległych trafień** (CR-008): wpisy zapisane bez tłumaczenia (limit przebiegu) dostają je później
  i trwale w `wpisy.jsonl`; na pulpicie i w mailach bez cyrylicy (oryginał tylko w podpowiedzi).
- Rozpoznanie strony działania w nagłówkach po rosyjsku (kanały LSM, ERR, LRT, BBC po rosyjsku).
- Archiwum wszystkich nagłówków z 7 dni (`dane/naglowki.jsonl` na gałęzi `dane`), także bez trafień wskaźników.

### Zmienione
- Sposób liczenia WW: wpisy, w których działa strona własna lub sojusznicza, nie liczą się do koncentracji wojsk,
  gotowości bojowej i dużych ćwiczeń przeciwnika (na danych z 4.11: 5 z 457 wpisów, m.in. „Poland mobilizes police
  and army at the border with Kaliningrad”). Wagi i progi bez zmian.
- Autoulepszanie czyta też lekcje z analizy wstecznej i werdykty modelu intencji.
- Skrót dnia: zdanie o analogii 2021/22 bez słowa „flanka” (mówi wprost: Polska, Bałtowie, kraje nordyckie, próg 2 redakcji w 30 dniach).
- Metodyka: nowe sekcje 8–10 (skan, intencja, kontrola jakości), źródła Heuer (1999) i Brier (1950).

## [1.5.1] - 2026-11-03
### Zmienione
- Metodyka: osobna sekcja „Bezpieczeństwo linków” (PR #11).

## [1.5.0] - 2026-11-03
### Dodane
- Ikona na pulpit telefonu (manifest, pełny ekran), sekcja metodyki dla znajomych (PR #10).

## [1.4.0] - 2026-11-03
### Dodane
- 12 źródeł nordyckich (SE, NO, DK, FI, IS), tłumaczenie sv/no/da, lista źródeł grupami region → kraj (PR #7).
### Zmienione
- Kraje nordyckie w geografii „flanka”, wyjątki domen linków, google.com jako znany fałszywy alarm VirusTotal (PR #9).

## [1.3.0] - 2026-11-03
### Dodane
- Kontrola każdego linku przy przebiegu i cotygodniowe sprawdzenie domen w VirusTotal (PR #6).

## [1.2.0] - 2026-11-03
### Dodane
- Harmonogram z zapasem (`13,43 * * * *`), workflow `czuwanie.yml` (PR #5).
### Zmienione
- Pillow 13.0 (PR #3).

## [1.1.1] - 2026-11-03
### Poprawione
- Koncentracja wojsk: bez własnych i sojuszniczych sił (PR #4). Przyczyna CR-005.

## [1.1.0] - 2026-11-03
### Dodane
- Etapy 1–4 planu ulepszeń: bezpieczeństwo i blokady kosztów, kontrola jakości, samouczenie, autoulepszanie (PR #2).

## [1.0.0] - 2026-11-02
### Dodane
- Pierwsza wersja w publicznym repo: źródła RSS z oceną A–F, słownik wskaźników, WW, alarmy mailem, strona na GitHub Pages.
