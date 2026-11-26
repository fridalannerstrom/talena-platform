# Ticket 507: e-postleveransstatus

## Inventering och omfattning

| Flöde | Mottagare | Befintlig loggning | Hantering i den här ändringen |
| --- | --- | --- | --- |
| Testinbjudan till kandidat | Kandidatens projektinbjudan | `EmailLog` kopplad till `TestInvitation` | Status, studs, adressrättning och omskick visas i kandidatvyn. |
| Kandidatrapport | Kandidat | `EmailLog` kopplad till `TestInvitation` | Separat mejlflöde; visas inte som bekräftat levererat utan spårbar providerhändelse. |
| Projektavslut | Projektägare | `EmailLog` kopplad till `TestInvitation` | Separat notisflöde; visas inte som bekräftat levererat utan spårbar providerhändelse. |
| Konto-/användarinbjudningar | Användare | Egen utskickslogik | Utanför kandidatens utskickshistorik. |

Första kundflödet är testinbjudan, ticketens prioritet. Azure Communication Services (ACS) skickar leveransrapporter till Event Grid; Talena matchar rapporten på Message-ID och exakt mottagaradress och sparar varje Event Grid-händelse med unikt provider-ID. Dubbletter kan därför tas emot utan att status eller historik dupliceras.

## Statusbetydelse

- `Skickas / väntar`: meddelandet är köat eller inväntar rapport.
- `Skickat`: utskickstjänsten accepterade meddelandet.
- `Levererat`: mottagarens e-postserver rapporterade att den tog emot meddelandet. Det garanterar inte inkorgsplacering eller läsning.
- `Kunde inte levereras`: ACS rapporterade ett avvisat eller studsat mejl.
- `Leveransstatus okänd`: leveransrapport saknas eller spårning har inte konfigurerats.

## Driftkonfiguration

Aktivera `EMAIL_DELIVERY_TRACKING_ENABLED=true` först när Event Grid-prenumerationen är konfigurerad. Sätt `ACS_EMAIL_EVENTGRID_SECRET` som hemlighet och konfigurera prenumerationens endpoint till `/webhooks/acs-email-delivery/?token=<secret>`. Endpointen svarar på Event Grid-valideringen och behandlar endast e-postleveransrapporter; öppningsspårning används inte.
