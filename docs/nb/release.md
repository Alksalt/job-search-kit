# Veiledning for offentlig publisering

Repositoriet og en personlig arbeidsmappe har ulike formål. Tillatelse til å publisere kode gir ikke tillatelse til å publisere kandidatopplysninger. Eksportverktøyet bruker `public-files.json`; det kopierer ikke hele mappen eller Git-historikken.

Se [SECURITY.md](../../SECURITY.md) for sikkerhetsavgrensning og rapportering. Kontroller med fiktive data, og beskriv feil uten å dele private dokumenter eller hemmeligheter.

## Kontroller og eksporter

Fra prosjektmappen:

```sh
python3 -m unittest discover -s tests
python3 -m jobkit demo
python3 -m jobkit.release check
python3 -m jobkit.release export --output "$HOME/job-search-kit-public-export"
```

Med uv setter du `uv run` foran de samme kommandoene. Filene uv lager (`.venv/`, `uv.lock` og en `*.egg-info/` på øverste nivå), ignoreres og eksporteres aldri.

Målet må være en ny mappe utenfor prosjektmappen. For en tilpasset kontroll kan du lage en privat liste med sensitive uttrykk utenfor repositoriet, ett uttrykk per linje. Oppgi filbanen uten å kopiere innholdet til en feilrapport eller samtale:

```sh
python3 -m jobkit.release check --deny-file "$HOME/job-search-private/release-deny.txt"
python3 -m jobkit.release export \
  --output "$HOME/job-search-kit-public-export-checked" \
  --deny-file "$HOME/job-search-private/release-deny.txt"
```

Bruk navn, private brukernavn, e-postadresser, telefonnumre, adresser, kontoidentifikatorer og private domener som gjelder din kopi. Ta med telefonnumre i norsk format; uten et uttrykk i listen gjenkjennes bare internasjonale numre med `+`. Ikke legg en ekte kontrolliste i den offentlige fillisten. Uttrykkene gjenkjennes i innhold og filnavn uavhengig av store og små bokstaver, Unicode-normalisering, et UTF-8-byte-rekkefølgemerke (BOM) eller usynlige formateringstegn som myke bindestreker, og i innhold også på tvers av linjeskift. Escape-sekvenser i JSON-, TOML- og Python-strenger og HTML-entiteter dekodes før kontrollen; det gjør ikke YAML-escape-sekvenser. En skanner kan finne mønstre og oppgitte uttrykk, men kan ikke bevise at all tekst og alle nye vedlegg er fri for personopplysninger.

Se gjennom de faktiske eksporterte filene før publisering. Kontroller fillisten, omtalen av opphavspersonen, eksempler, kommentarer, avhengighetsfiler og repository-adresser. Utelat lokale instruksjoner, skjulte innstillinger, databaser, kvitteringer, CV-er, søknadsbrev, skjermbilder, sikkerhetskopier, samtalelogger og hemmeligheter. Kontroller både filnavn og innhold. Hver ny fil trenger en uttrykkelig beslutning om den skal være offentlig.

Eksporten er en ren mappe, ikke et publisert GitHub-repositorium. Opprett ny Git-historikk der hvis du vil publisere. Ikke gjenbruk et privat prosjekts `.git`-mappe eller last opp den opprinnelige arbeidsmappen. GitHub-publisering er en egen brukerhandling eller krever et uttrykkelig oppdrag.

I en Git-mappe avviser `check` også sporede filer utenfor fillisten, sporede lenker eller undermoduler og funn i det klargjorte (staged) innholdet i filene på listen. Tidligere innsendinger (commits) kontrolleres aldri. En `.git`-pekerfil for en tilknyttet arbeidskopi (linked worktree) godtas og eksporteres aldri. Den eneste fullt kontrollerte publiseringsveien er denne rene eksporten med ny Git-historikk; en eksisterende historikk må gjennomgås separat.

## Vurderinger og begrensninger

Les [gjennomgangsloggen](../../REVIEW.md) for kontroller som faktisk er utført, og funn som er rettet. Lokale tester og en fiktiv demonstrasjon bekrefter ikke at en virkelig portal, leverandørkonto, tidsplan eller innsending virker. Kontroller på nytt etter endringer; tidligere resultater gjelder bare filene som ble gjennomgått.

## Hvis private opplysninger er publisert

Stans videre publisering. Tilbakekall først eventuell eksponert innloggingsinformasjon. Fjern så opplysningene og undersøk historikk, forgreninger og kopier. Følg [GitHubs veiledning for fjerning av sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). Sletting av dagens fil fjerner ikke eldre Git-innsendinger. Ikke lim inn den sensitive verdien i en offentlig hendelsesrapport.
