# Job Search Kit

[English](README.md)

En lokal arbeidsflyt for jobbsøkere som bruker Codex, Claude Code eller begge. Samle dokumenterte kandidatopplysninger, vurder stillinger, gjenbruk godkjent søknadstekst og registrer søknadsforsøk med dokumentasjon. Veiledninger og oppgavebeskrivelser finnes på engelsk og bokmål.

Dette er en ny, offentlig implementasjon. Den inneholder ingen ekte kandidatprofil, søknadsoppføringer eller kontooppsett. Et eget [erfaringsnotat](docs/nb/experience.md) deler opphavspersonens samlede resultater og lærdommer fra den opprinnelige private arbeidsflyten, med personens tillatelse. Resultatene er ikke en evaluering av dette offentlige verktøyet, og verktøyet lover ikke bestemte jobbresultater.

## Prøv en demonstrasjon uten nettverk

Du trenger Python 3.11 eller nyere. Kjør kommandoene fra denne mappen. Selve verktøyet krever ingen Python-pakker eller API-nøkler.

Eksemplene bruker et POSIX-skall. På Windows kan du be agenten tilpasse dem til installert Python og kommandoskall; Windows er ikke testet lokalt.

```sh
python3 -m jobkit --help
python3 -m jobkit demo
```

Demonstrasjonen bruker fiktive data og sender ingenting. Opprett en privat arbeidsmappe **utenfor denne prosjektmappen og utenfor alle Git-repositorier** når du skal bruke egne opplysninger:

```sh
python3 -m jobkit --workspace "$HOME/job-search-private" init --language nb
python3 -m jobkit --workspace "$HOME/job-search-private" verify
```

Opprettelsen lager `candidate.md` og `preferences.md` i den private arbeidsmappen. Fyll dem ut med egne opplysninger, eventuelt ved hjelp av de utvidede [tomme malene](templates/). Oppbevar CV-er, søknadsbrev, skjermbilder fra portaler, kvitteringer og kontoinformasjon privat. Ikke legg personopplysninger i dette repositoriet eller i offentlige feilrapporter.

Vil du heller starte gjennom agenten? Åpne prosjektmappen i Codex eller Claude Code og lim inn:

> Les AGENTS.md og hjelp meg å sette opp mitt eget jobbsøk. Kontroller Python 3.11 eller nyere, spør om ønskede stillinger, steder, språk og bindende kriterier, og opprett en tom privat arbeidsmappe utenfor prosjektmappen og alle Git-repositorier. Hjelp meg å fylle ut kandidatopplysninger og ønsker med kilder jeg gir; la udokumenterte forhold stå som ukjente. Begynn bare med stillingssøk. Ikke opprett en tidsplan eller send søknader uten at jeg uttrykkelig ber om det.

## Kom i gang

- [Arbeidsflyt for jobbsøk og kontrollert innsending](docs/nb/workflow.md).
- [Valgfrie automatiseringer i Codex og Claude](docs/nb/automations.md).
- [Oppgavebeskrivelser på bokmål](prompts/nb/) og [engelsk](prompts/en/).
- [Kilder og designvalg](docs/nb/research-design.md) og [utviklingsplan med kjente begrensninger](BUILD_PLAN.md) (på engelsk).
- [Erfaringer fra det opprinnelige jobbsøket](docs/nb/experience.md), med avslag, intervjuer og begrensninger i underlaget.
- [Kontroll og eksport av offentlig versjon](docs/nb/release.md).

Kommandolinjeverktøyet registrerer dokumentasjon og kontrollerer overganger i arbeidsflyten. Det styrer ikke nettleseren, installerer ikke tidsplaner, kobler seg ikke til NAV og synkroniserer ikke Notion. Bruk de datamaskin- og nettleserverktøyene agenten faktisk har tilgang til, innenfor plattformens regler og ditt uttrykkelige oppdrag. Operatøren skal kontrollere den faktiske portalen før innsending.

Ukjent sendestatus betyr at eksisterende forsøk må avklares før noe nytt sendes. Bare én operatør skal styre nettleseren på en maskin om gangen. Verktøyet kan registrere operatørens dokumentasjon, men kan ikke selv bevise hva portalen viste eller mottok.

## Bidra

[AGENTS.md](AGENTS.md) viser hvor agenter skal begynne. Bruk bare fiktive testdata og eksempler. Utover det uttrykkelig godkjente erfaringsnotatet med samlede resultater og navngivelsen av opphavspersonen skal dokumentasjonen være fri for kandidatopplysninger og innloggingsinformasjon. Følg [publiseringsveiledningen](docs/nb/release.md) før du deler en kopi.

[Opphavsperson](README.md#attribution).
