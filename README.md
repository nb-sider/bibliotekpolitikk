# Bibliotekpolitikk-overvåking

Overvåker regjeringen.no og stortinget.no for omtale av **bibliotek**, **lesestrategi**, **leselyst**, **Nasjonalbiblioteket** og **kulturarv**. Oppdateres automatisk hver mandag morgen via GitHub Actions, og resultatet vises som en nettside (GitHub Pages).

## Oppsett (gjøres én gang, ca. 5 minutter)

1. **Opprett repo**: Logg inn på github.com → «New repository» → gi det et navn (f.eks. `bibliotekpolitikk`) → velg «Public» → «Create repository».

2. **Last opp filene**: «uploading an existing file» → dra inn alle filene i denne mappen (inkludert den skjulte `.github`-mappen — last opp via git eller bruk «Add file → Create new file» med filnavn `.github/workflows/ukentlig.yml` og lim inn innholdet). Enklest med git fra terminalen:

   ```
   cd github-repo
   git init && git add -A && git commit -m "Første versjon"
   git branch -M main
   git remote add origin https://github.com/BRUKERNAVN/bibliotekpolitikk.git
   git push -u origin main
   ```

3. **Slå på Pages**: Repoets «Settings» → «Pages» → under «Build and deployment» velg «Deploy from a branch» → branch `main`, mappe `/ (root)` → «Save».

4. **Gi Actions skrivetilgang**: «Settings» → «Actions» → «General» → under «Workflow permissions» velg «Read and write permissions» → «Save».

Ferdig. Nettsiden ligger på `https://BRUKERNAVN.github.io/bibliotekpolitikk/` etter et par minutter. Send den lenken til de som skal bruke løsningen.

## Hvordan det virker

- **Hver mandag kl. 07/08 norsk tid** kjører GitHub Actions scraperen i skyen. Den henter bare *nytt* siden sist (tilstanden ligger i `tilstand.json`), verifiserer treffene mot sidenes faktiske innhold, og committer oppdatert `treff.json`, `treff.csv` og nettside.
- **Nye treff** merkes med oransje «NY» på nettsiden, og kan filtreres frem med «Bare nye».
- **Manuell kjøring**: Actions-fanen → «Ukentlig oppdatering» → «Run workflow».
- **Rådata**: `treff.csv` kan åpnes i Excel (og analyseres med Copilot).

## Vedlikehold

- GitHub kan pause planlagte kjøringer i repo uten aktivitet over lengre tid. Får dere e-post om dette: gå til Actions-fanen og trykk «Enable workflow».
- Søkeord endres øverst i `bibliotekpolitikk_scraper.py` (`KEYWORDS`).
- Slutter regjeringen.no-delen å gi treff, har nettstedet trolig endret HTML-struktur — da må `scrape_regjeringen()` justeres.
- Kontakt-e-posten i `HEADERS` i scriptet bør endres til ny eier.
