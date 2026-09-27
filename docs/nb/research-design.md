# Kilder og designvalg

Kildene ble kontrollert 27.09.2026. Funksjoner hos leverandørene kan endres; bruk primærkildene når du setter opp din installasjon. Tabellen skiller dokumenterte muligheter fra prosjektets egne valg.

| Kildegrunnlag | Valg i prosjektet |
| --- | --- |
| Codex dokumenterer datamaskinbruk med vilkår for tilgang og plattform. [Kilde](https://learn.chatgpt.com/docs/computer-use) | Kontroller tilgjengelige verktøy ved kjøring; ikke bygg inn en universell nettleserdriver. |
| Lokale Codex-automatiseringer avhenger av at det lokale miljøet kjører. [Kilde](https://learn.chatgpt.com/docs/automations?surface=app) | Lever tydelige oppgavebeskrivelser og oppsettsveiledning; ikke installer en tidsplan i bakgrunnen. |
| Claude beskriver datamaskinbruk, en egen nettleserintegrasjon og tidsplaner med ulik levetid. [Skrivebordsapp](https://code.claude.com/docs/en/desktop), [tidsplaner](https://code.claude.com/docs/en/scheduled-tasks) | Bruk samme prosess hos begge leverandører og bare én nettleseroperatør. |
| Claude støtter ferdigheter definert i lokale filer. [Kilde](https://code.claude.com/docs/en/skills) | Første versjon bruker vanlige veiledninger og oppgavebeskrivelser; en egen ferdighetspakke er ikke nødvendig. |
| NAVs stillingsstrøm bruker JWT og krever håndtering av token, oppdateringer og fjerninger. [Kilde](https://navikt.github.io/pam-stilling-feed/) | Utsett integrasjonen. Agentsøk og eksplisitt stillingsregistrering støttes, uten å love en fullstendig stillingsoversikt. |
| Fjerning av sensitive opplysninger etter Git-publisering kan kreve rydding i historikk og samordning. [Kilde](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) | Bygg nye filer, hold private data utenfor Git og eksporter bare filer i en uttrykkelig offentlig liste. |

Vi vurderte en renset kopi av et privat prosjekt, en nettjeneste og en ren samling oppgavebeskrivelser. Et nytt lokalt verktøy gir en mindre dataflate og en konkret logg over søknadsforsøk uten å importere historikk eller lagre kandidatdata på en server. [Utviklingsplanen](../../BUILD_PLAN.md) beskriver omfanget.

Verktøyet kan kontrollere lokale registreringer og filintegritet. Det kan ikke avgjøre om kandidatpåstander er sanne, om et nettsted tillater automatisering eller om en portal mottok søknaden. Det krever kilder, brukerens oppdrag og operatørens faktiske observasjoner. Ukjent sendestatus skal avklares, ikke utløse automatisk nytt forsøk.

Fremtidige integrasjoner bør være valgfrie og avgrensede: autentiserte stillingsstrømmer som håndterer endringer, tilkobling til et valgfritt sporingssystem og bedre eksport av dokumentasjon. Hver integrasjon tilfører dataflyt som krever egen personvernvurdering. Ingen av dem inngår i denne versjonen.
