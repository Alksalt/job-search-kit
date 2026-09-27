# Valgfrie automatiseringer

Python-verktøyet oppretter ikke tidsplaner og styrer ikke datamaskinen. Du velger agent, kontrollerer tilgjengelige verktøy og oppretter hver tidsplan selv eller ber agenten uttrykkelig om det. Bruk den offentlige prosjektmappen for kode og veiledninger, og den private arbeidsmappen for personlige opplysninger.

## Første kjøring med begge leverandører

1. Åpne prosjektmappen i agenten og les `AGENTS.md`.
2. Oppgi absolutt filbane til den private arbeidsmappen og hvilke kilder og filer agenten kan lese. Kontroller leverandørens personverninnstillinger før du deler sensitive opplysninger.
3. Be agenten kjøre `python3 -m jobkit --help` og kontrollere arbeidsmappen uten å endre noe. Behold valgt modell; prosjektet krever ingen bestemt modell.
4. Kjør hver valgt oppgave manuelt én gang. Kontroller resultat, datoer, kildelenker og endringer før du lager en tidsplan.
5. Bekreft tidssone, hyppighet, kildevalg og tillatte endringer. Et planlagt stillingssøk er ingen tillatelse til å sende søknader.

Hver planlagte oppgave lagrer en datert privat rapport i `<arbeidsmappe>/reports/` som sier om kjøringen ble fullført eller mislyktes, hva som ble kontrollert og hvilke handlinger som gjenstår, også ukjente, løpende og passerte frister. Les rapportene; mangler en rapport, ble kjøringen ikke fullført. Før du tar sikkerhetskopi av, flytter eller oppgraderer arbeidsmappen eller verktøyet, må du stoppe alle tidsplaner og følge [trinnene for sikkerhetskopi og oppgradering](workflow.md#sikkerhetskopi-gjenoppretting-flytting-og-oppgradering).

## Codex

Bruk datamaskinverktøyene installasjonen faktisk tilbyr. Tilgang avhenger av operativsystem, konto og innstillinger. Kontroller [OpenAIs veiledning for datamaskinbruk](https://learn.chatgpt.com/docs/computer-use) før du regner med at en eksisterende nettleserøkt er tilgjengelig.

Opprett gjentakende oppgaver gjennom appens støttede funksjon. Lokale kjøringer krever at maskinen er på og appen kjører. Se [OpenAIs veiledning for automatiseringer](https://learn.chatgpt.com/docs/automations?surface=app). Tekstene nedenfor er oppgavebeskrivelser, ikke ferdig installerte tidsplaner.

## Claude Code

Åpne prosjektmappen; `CLAUDE.md` laster fellesinstruksjonene i `AGENTS.md`. [Veiledningen for skrivebordsappen](https://code.claude.com/docs/en/desktop) beskriver gjeldende støtte og begrensninger for datamaskinbruk. Visning av nettsider og interaktiv nettleserstyring er ulike funksjoner. Bruk den egne Chrome-integrasjonen når nødvendig interaksjon krever den, og kontroller tilgangene.

Velg tidsplan med omhu: `/loop` i en økt og varige tidsplaner i skrivebordsappen har ulik levetid. Kontroller hvilken du oppretter i [veiledningen for planlagte oppgaver](https://code.claude.com/docs/en/scheduled-tasks). Repositoriet oppretter ingen løkke, cron-oppføring eller bakgrunnsjobb.

## Oppdrag du kan kopiere

Bytt ut alle `<...>` før bruk. Agenten må avklare avgjørende mangler i oppdraget. Tidspunktene er eksempler, ikke innstillinger som allerede er tatt i bruk.

**Daglig stillingssøk, for eksempel 08.30:**

> Opprett en valgfri daglig oppgave klokken 08.30 i `<tidssone>`. Bruk prosjektmappen `<prosjektmappe>` og den private arbeidsmappen `<arbeidsmappe>`. Følg `prompts/nb/discover.md`, søk bare i `<godkjente kilder>` etter `<stillingstyper>` og finn høyst `<antall>` relevante nye stillinger. Du kan registrere og vurdere stillinger i arbeidsmappen. Ikke kontakt noen eller send søknader. Hvis miljøet ikke kan kjøre denne tidsplanen, forklar begrensningen uten å hevde at den er opprettet.

**Daglig fristkontroll, for eksempel 09.00:**

> Opprett en daglig oppgave klokken 09.00 i `<tidssone>`. Bruk `<prosjektmappe>` og `<arbeidsmappe>`, og følg `prompts/nb/deadlines.md`. Se gjennom frister de neste sju dagene og alle passerte, ukjente eller løpende frister, kontroller vesentlige endringer i originalannonsene og oppgi i den daterte rapporten hva som er blokkert. Ikke send søknader eller meldinger.

**Ukentlig gjennomgang, for eksempel fredag 16.00:**

> Opprett en ukentlig oppgave fredag klokken 16.00 i `<tidssone>`. Bruk `<prosjektmappe>` og `<arbeidsmappe>`, og følg `prompts/nb/weekly-review.md`. Oppsummer registrert fremdrift, uavklarte søknadsforsøk og neste handlinger. Foreslå endringer; ikke endre søkekriteriene mine, skriv ny søknadstekst eller kontakt noen uten et eget oppdrag.

**Kontrollert innsending er et eget uttrykkelig oppdrag:** bruk [søknadsoppgaven](../../prompts/nb/apply-supervised.md) for en angitt gruppe stillings-ID-er. Ikke legg den til tidsplanene ovenfor. En eksisterende godkjenning gjelder fortsatt innenfor sitt nøyaktige omfang, men gir ikke tillatelse til nye arbeidsgivere eller fremtidige søknadsrunder.

Stopp eller slett en tidsplan gjennom samme leverandør som opprettet den, og kontroller statusen etterpå. Stopp gamle tidsplaner før du bytter leverandør, slik at oppgaver ikke kjøres dobbelt. En fullført agentoppgave beviser ikke at arbeidsgiveren har mottatt en søknad; se på kvitteringen.
