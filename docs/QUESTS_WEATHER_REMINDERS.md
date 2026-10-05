# Care quests, district weather and reminders

## Try the feature

Sign in → **Saved care plans** → open a latest plan → **Care quests & weather**.
Reviewed content is still pending in the development catalog. No demo/draft record
becomes a plan or quest. An empty list is expected until a qualified reviewer and
rights-cleared sources supply real content. Synthetic approved fixtures are only
used in disposable tests, never live recommendations.

The board includes daily observations, active weekly instruction reviews, a
pending count, completion/undo, forecast state, weather opt-in/withdrawal and a
separate generic device reminder. Refresh manually, on resume or every five
minutes while this screen is active. Failed refresh hides previous tasks instead
of presenting unverifiable cached advice as current. No offline queue/background
forecast worker is implemented for this board. Manual care and downloaded plans
now have a separate [offline notebook](OFFLINE_CARE.md); quest completion/forecast
adaptation still stay online and do not use cached weather.

## Tasks and safeguards

- Bangladesh civil dates: daily observations run days1 through the plan's final
  day; preparation appears on day0 only. Future/finished plans do not invent
  today's tasks. `days=1..7` optionally includes upcoming tasks; responses are
  bounded by the existing reviewed directive cap.
- Daily means a generic observation, **not a sourced irrigation action**. Weekly
  means review/follow the existing cited instruction this week. Sources have week
  ranges, not exact action frequencies: never invent daily watering, weekly
  fertilizer, doses, treatments or a new care instruction.
- Reviewed text/citations remain unchanged. Rain ≥5mm and probability ≥60% adds
  a soil/shelter check note to watering reviews; max temperature ≥35°C adds a
  heat/stress observation note. These are prototype monitoring-alert thresholds,
  not agronomic dosing rules or formal heatwave diagnosis. Both may appear.
  Forecasts cannot establish pot moisture, shelter or actual rainfall. The app
  does **not** automatically skip/increase watering or change doses.
- Stale/unavailable forecasts produce visible warnings and no adaptation.
  Base reviewed instructions remain unchanged. Changed/expired/withdrawn plan
  evidence withholds **all tasks** and rejects completion; revise the plan.
- Completion is self-reported check/review, not proof of care, survival or rewards.
  Owner + plan version + stable task key deduplicate retries. Undo affects only
  that user's completion. Weather changes don't change keys. New versions have
  independent completions and weather opt-in; historical records remain private.
- Only current active tasks can be completed: future/unknown/old-version tasks
  return409. Missed daily observations aren't automatically completed or shifted.
  No passport linkage or automatic manual-care-history entry is invented.

## Provider setup, privacy and rights

Operator default is `WEATHER_MODE=disabled`. After reviewing current service terms,
for a **non-commercial prototype only**, set `WEATHER_MODE=open-meteo-noncommercial`
in private `.env` and recreate the API. Do not commit `.env`. Commercial/paid
access is not implemented; deployment needs a separately approved configuration.

Users separately opt in per saved version with notice `weather-2026-10-05`.
General account consent preferences do not enable weather. Only chosen, saved
Bangladesh district precision is supported; none/country precision isn't upgraded.
Supported English/Bangla aliases: Dhaka, Chattogram, Rajshahi, Khulna, Sylhet,
Rangpur, Barishal, Mymensingh. Weather reference coverage is not agricultural
approval or complete district coverage. Unsupported/stale/no-permission plans
never make provider calls.

Only a fixed approximate **city reference point** and weather variables go from
the server to the fixed HTTPS Open-Meteo endpoint. No GPS, address, account ID,
plant name, goal/soil prose or bearer is sent. No geocoder/user URL is accepted.
Open-Meteo sees the server IP/reference coordinate and states that troubleshooting
request logs may last90 days. Withdrawal stops future requests for that version;
in-flight requests cannot be unsent and provider logs cannot be erased by Groot.
Other consenting users can still request the same public regional forecast.

The normalized latest forecast (max7 days) is a shared **eight-key cache**, not
user location history; no owner/plan association is stored. A PostgreSQL claim
limits attempts, including failures, to once per district per15 minutes across
workers/accounts (~768/day maximum across8 keys). Authorization is rechecked
before/after network I/O; no account/plan locks or DB connections span a provider
call. Cache cannot bypass ownership/evidence. Late responses cannot replace newer
claims. A changed version/withdrawal during fetch prevents use by that request.
Private routes retain TLS, input redaction, request bounds, rate limits/no-store.

Adapter: fixed HTTPS host, no redirects,5-second socket timeout,64KiB response
cap, strict units/timezone/array/date/finite-value validation, no leaked provider
errors. This socket timeout is not a hard overall DNS/slow-trickle deadline;
production needs reviewed egress/total request deadlines and monitoring.

Freshness means retrieved <6 hours ago, no future retrieval timestamp, and today's
Bangladesh date is covered. **Model issue time isn't supplied** by this endpoint;
`generationtime_ms` is computation duration, not a timestamp. UI labels retrieval
time and unknown model age. No BMD integration or plot-level accuracy is claimed.
Stale data may remain in the bounded cache but never adapts tasks. Each key is
replaced on successful fetch. Preferences/completions cascade only on explicit
plan/account deletion; public regional cache is unrelated to account retention.

Displayed attribution: **Weather data: Open-Meteo (CC BY4.0)**, provider link and
regional-estimate disclaimer. Agricultural directive rights remain independent.

Primary sources checked2026-10-05:

- [Forecast fields, units, timezone and timestamp semantics](https://open-meteo.com/en/docs).
- [Open-Meteo service terms and request-log privacy](https://open-meteo.com/en/terms):
  free access is non-commercial with usage limits; review before deployment.
- [CC BY4.0](https://creativecommons.org/licenses/by/4.0/).

This is not legal clearance, a service-availability guarantee or crop validation.

## Reminders

In-app count lists active incomplete checks/reviews without OS permission. No
push/email/SMS service, device-token registration or paid provider is introduced.

Optional Android reminder: choose a **device-local** time and allow Android13+
notifications if desired. A single generic device-wide daily alarm says “Open
Groot to recheck current care tasks”; no watering command, plant name, location,
private content or bearer. It doesn't promise tasks are due. Only an enabled
boolean is saved in app-private preferences; the OS retains alarm schedule time.
Denial or channel blocking leaves in-app reminders available.

Uses an **inexact repeating alarm**, no exact-alarm/background location permission.
Android Doze/battery controls can delay delivery. No background weather fetch or
task action occurs in the receiver. Tap to open, reauthenticate and recheck current
evidence. Disable in Groot/Android settings. Sign-out,401, password/account
deletion, closing the private garden and a new Flutter engine/app restart cancel
the alarm and displayed reminder. Late permission callbacks cannot revive it.
Force-stop/reboot can discard alarms; no boot/timezone recovery. Re-enable after
restart/timezone change; user choice is not automatically restored. A previously
opted-in generic reminder can fire while the process is closed before next startup,
but cannot access any account/private instruction.

References: [Android inexact alarms](https://developer.android.com/develop/background-work/services/alarms/schedule),
[notification permission](https://developer.android.com/develop/ui/views/notifications/notification-permission).

## Private HTTP contracts

Latest versions only. Clients cannot submit owners, snapshots or forecast data.

| Method/path | Contract |
| --- | --- |
| `GET /v1/plans/{id}/quests?days=1` | Server-generated current board; days1..7 |
| `POST /v1/plans/{id}/quests/completion` | `{version,key,completed}`; retry-safe completion/undo |
| `PUT /v1/plans/{id}/quests/weather` | `{enabled,notice_version:"weather-2026-10-05"}`; preference write doesn't fetch |

## Migration and verification

Revision0006 adds only completion, per-version weather preference and regional
cache tables/indexes. Original rows/snapshots remain intact. FKs enforce owner/plan
and plan/version. Downgrade is blocked to preserve private data; use a forward fix.
Follow [backup/restore procedures](DATABASE_MIGRATIONS.md) before upgrading a real
DB. Never reset a volume or stamp history.

```sh
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
# After backup and restore rehearsal:
docker compose build api migrate
sh scripts/db.sh upgrade
sh scripts/db.sh check  # current head 0009 (quest tables begin at 0006)
docker compose up --build --wait
```

Tests mock weather; CI never depends on live forecast availability. The existing
GitHub mobile SDK setup failure is separate; this feature task does not commit,
push, rerun remote jobs or alter staged editor files.
