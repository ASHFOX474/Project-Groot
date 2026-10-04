# Plant source access and reuse review

Checked **2026-10-04**. Purpose: source-traceable Bangladesh plant requirements,
not a bulk scrape or a legal opinion. Public access is separate from permission
to adapt/redistribute, and evidence checking is separate from agronomic approval.

## Findings and decisions

| Source / exact artifact | Access observed | Reuse finding | Decision |
| --- | --- | --- | --- |
| [BARC/AFACI handbook PDF](https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-barc/2024/12/053a0722429448d4903412ce683a7d06.pdf) | Public PDF readable, with crop production chapters | No artifact-specific reuse grant verified | Small independent factual research drafts with page citations; permission pending; no recommendation eligibility |
| [BARC crop calendar portal](https://apps.barc.gov.bd/cropcalendar/) | Login/signup required for calendars | Indexed footer reports both commercial-use prohibition and CC BY4; direct rendered text does not settle the conflict | No account creation or calendar import; request written artifact-specific clarification before reuse |
| [AIS](https://ais.gov.bd/) and [DAE](https://dae.gov.bd/) | Official discovery candidates; indexed articles visible, direct fetches timed out/failed in this session | No site/artifact reuse permission verified | Access/reuse unverified; no article import |
| [SRDI](https://srdi.gov.bd/) | Direct fetch timed out | No reuse license verified | Candidate for site-specific soil guidance; not a substitute for a plot/pot soil test; no import |
| [BFRI SUFAL manuals](https://bfri.gov.bd/site/page/41e0159a-91ca-4b96-ba3b-36f6ee9c8500/) and [BFRI apps](https://bfri.gov.bd/site/page/d1c32c9e-df2d-4c7d-a463-7ab8f150f300) | Indexed nursery/tree resources; direct access failed/timed out | No exact manual/app dataset license verified | Forestry candidates, not usable machine-readable care data yet; no app/binary scraping |
| [Forest Department seedling page](https://bforest.gov.bd/pages/static-pages/6922dd23933eb65569e13a6f) / [BFIS](https://bfis.bforest.gov.bd/bfis/) | Discovery candidates; exact seedling page retrieval failed | No reuse grant verified | Do not infer requirements or native status from a discovery listing |
| [ICRAF Neem factsheet, AFT4.0, 2009](https://apps.worldagroforestry.org/treedb/AFTPDFS/Azadirachta_indica.pdf) | Public 8-page PDF readable | No reuse license verified for this exact work/version | Limited global ecological facts as a draft; local applicability and permission pending |
| [TreeGOER2024.07, Zenodo13132613](https://zenodo.org/records/13132613) | Direct public API GET succeeded, HTTP200 | [Exact-version API](https://zenodo.org/api/records/13132613) reports `access_right=open`, `license.id=cc-by-4.0` | Reusable candidate with attribution; only metadata registered, no environmental dataset imported or care thresholds inferred |

A tool timeout is not proof a site is permanently unavailable. Dates above are
inspection dates, not document publication dates. Government ownership does not
automatically imply public-domain/open-license content. The national portal's
[terms](https://bangladesh.gov.bd/pages/static-pages/69a55ba386514399668e4e70)
describe unmodified printing and third-party permissions; that does not establish
a blanket license to build an adapted app database across agencies.

TreeGOER's [author publication](https://onlinelibrary.wiley.com/doi/10.1111/gcb.16914)
explains its observed environmental distributions and identifies database reuse
under CC BY4. The version-specific metadata resolves the otherwise blank license
in the web renderer. Attribute both the dataset/version DOI and associated paper
when using data; verify exact files and their integrity before a later import.
The publisher checksum in `services/api/catalog/treegoer-access-evidence.json`
is recorded, **not independently verified**: the data file was not downloaded.
No license was transferred from TreeGOER or a different AFT listing to the Neem PDF.

## Included research draft

`services/api/catalog/bangladesh-starter-v1.json` contains three plants, three
source records (including the reusable TreeGOER registry entry), three profiles
and eleven field-level facts. Every fact has its own source ID, section/page
locator and interpretation note. The source registry is not a license grant.

- Okra: pH, preferred textures, general field spacing and approximate sowing windows
  from handbook printed pp91–92 (PDF pages105–106, 1-based).
- Winter tomato: pH, production temperature, main-field spacing and seed-sowing
  window from printed p75 (PDF page89, 1-based). Summer varieties are not generalized.
- Neem: global preferred pH, drainage and light interpretations from AFT p2. This
  is not verified Bangladesh site suitability, native status or container advice.

Only minimal independently normalized factual values were recorded, not source
prose, images, full tables or chemical treatment instructions. Handbook spellings
and OCR need scrutiny; the Okra scientific-name spelling was normalized rather
than carrying over its typo. Missing facts remain absent, not filled with generic
LLM knowledge. Mid-month windows use day15 only as an explicit draft approximation.
No rainfall range became an irrigation schedule; no hectare dose became a pot dose.

All three profiles are **draft**. Their two actual requirement sources have
`permission_pending`; the registered TreeGOER source alone does not clear them.
The source reviewer string records an AI evidence check, **not an agronomist's
approval, publisher permission or field trial**. Candidate output should be empty.

## Needed before promoting a record

1. Recheck the exact source artifact and obtain a verified reuse license or written
   permission covering intended adaptation/redistribution and commercial use.
2. Have an appropriate Bangladesh agriculture/forestry reviewer assess each
   field, variety, locality, season, growing context, uncertainty and stale guidance.
3. Record reviewer/date/expiry, attribution and permission evidence; leave unknown
   or contradictory fields unresolved. Do not mark every Bangladesh district
   suitable from a country-level source.
4. Review/import a new immutable version using the workflow below; never promote
   `demo-*` or `starter-samples`, falsify permission, or silently edit a published bundle.
5. Rerun safety tests. Personal suitability still requires location/space/soil/sun
   inputs and a separately implemented matching service.

No agencies were contacted, accounts created or protected pages bypassed. Requests
for permissions or expert review require separate user authorization.

## Methodology and limitations

Examined primary agency pages, government-hosted and ICRAF PDFs, the author paper,
and exact Zenodo API metadata. A parallel read-only tree-source review supplemented
the crop review. Exa/Firecrawl connectors were unavailable; direct web search and
HTTPS requests were used. Several agency retrievals failed; no completeness claim
is made. The bundled data is intentionally small and quarantined, not an exhaustive
Bangladesh catalog. Access and terms can change; the first recheck deadline is
2027-01-02, not a guarantee that evidence stays valid until then.
