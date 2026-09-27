# Contributing / Bidra

Use invented examples. Reproduce a problem without a real CV, job-search history, screenshot, account token or private path. Keep runtime workspaces outside the source repository. Changes to application state transitions need tests for failures and recovery, not only the successful path.

Bruk fiktive eksempler. Gjenskap feil uten ekte CV-er, søknadshistorikk, skjermbilder, kontonøkler eller private filstier. Oppbevar arbeidsdata utenfor kildekoderepositoriet. Endringer i innsendingstilstandene må testes for feil og gjenoppretting, ikke bare vellykket innsending.

```sh
python3 -m unittest discover -s tests -v
python3 -m jobkit demo
python3 -m jobkit.release check
```

Add each intentional public file to `public-files.json` after reviewing its contents. Do not loosen the manifest or privacy check to admit a runtime artifact. Update English and Bokmål guides together when behavior changes. Use the configured agent/model; this repository does not need provider API credentials.

Legg hver ny offentlig fil til i `public-files.json` etter innholdskontroll. Ikke svekk publiseringskontrollen for å ta med arbeidsdata. Oppdater engelsk og bokmål samtidig når virkemåten endres. Bruk den konfigurerte agenten og modellen; repositoriet trenger ingen API-nøkler fra modelltilbydere.

The project uses the MIT license. A public contribution must be material you are authorized to share under that license.

Prosjektet bruker MIT-lisensen. Offentlige bidrag må være materiale du har rett til å dele under denne lisensen.
