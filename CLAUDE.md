# Wczesne Ostrzeżenie

Publiczny pulpit sygnałów zagrożenia wobec Polski i Bałtów (Python + RSS, GitHub Actions co godzinę, strona w GitHub Pages). Opis działania: `README.md`, plany: `docs/`.

## Reguły globalne (linki, nie kopie)
Reguły rozmowy wczytują się z `~/.claude/CLAUDE.md`. Reguły pracy w repo:

@~/.claude/rdzen/reguly/praca_w_repo.md

Brak `~/.claude/rdzen`: `git clone https://github.com/Climbat1ze/claude-rdzen.git ~/.claude/rdzen` (repo prywatne; w sesji bez dostępu pracuj według tego pliku).

Nie obowiązują tu: rejestr projektów i dane prywatne z innych repo. To repo jest publiczne.

## Reguły tego repo
- **Publiczne repo.** Żadnych wartości sekretów, adresów odbiorców maili ani danych osób w plikach i commitach; tylko nazwy zmiennych (`SMTP_USER`, `SMTP_PASS`, `MAIL_DO`, token Claude).
- Stan i decyzje projektu: `CHANGELOG.md`, `docs/`. Dokumenty z monorepo `PROJEKTY-CLAUDE-MASTER` (`PROJEKT WCZESNE OSTRZEZENIE/`) przejdą do `docs/` przy podziale monorepo.
