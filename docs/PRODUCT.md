# Product brief

## Goal

Groot helps people in Bangladesh choose locally suitable plants and keep them alive. Its core loop is goal and growing conditions → suitable species → care plan → daily or weekly tasks → check-ins → survival milestones.

The first users to design for are rooftop or home gardeners and smallholder growers using low-cost Android phones. A later organizer view can aggregate survival trends without revealing individual home locations.

## Source concept and claims

The one-page Groot concept paper is the product reference. It describes Bangla-first voice or text input, locally grounded recommendations, weather-aware care quests, photo check-ins, rewards, and offline use. This starter does not treat the paper's projected benefits or technical choices as verified outcomes.

Catalog and advice data should eventually come from reviewed, attributable Bangladeshi sources such as BARC, SRDI, DAE, and validated local plant-health images. Confirm current access, licensing, coverage, and update frequency before integration. Weather provider selection also needs a data-use and reliability review.

## Trust rules

- Show recommendation sources and the date they were reviewed.
- Ask for the user's growing environment; distinguish ground soil from rooftop containers.
- Use region-level data as context, not as a substitute for a user's plot or pot conditions.
- Show possible symptoms and uncertainty in photo analysis; serious or uncertain cases can be directed to the 16123 agricultural helpline after confirming its current availability.
- Treat photos as evidence of visible condition. Do not claim they prove every care action or survival with certainty.
- Make photo sharing and precise location optional. Keep private locations out of public leaderboards.
- Reward ongoing care and survival milestones at 3, 6, and 12 months. Normalize community scoring so users with many plants do not dominate by volume alone.

## Current starter scope

The preview catalog includes explicit demo rows and can include source-checked
research records. Neither browsing nor a source's `reviewed` evidence flag is
planting approval. A separate candidate-data boundary excludes demo, drafts,
expired reviews and uncleared rights. The first crop/tree research profiles remain
draft; no recommendation-eligible profiles ship yet. See
[source findings](CATALOG_SOURCES.md) and [import policy](CATALOG_IMPORT.md).

## First real product slice

Local handle/password accounts, editable optional choices and private Plant
Passports/manual care history are implemented. Names and care are self-reported,
not validated plant identification or survival evidence. There is no sharing,
GPS, photos, analytics, email recovery or offline synchronization. Use test data
in the HTTP preview; see [privacy/storage limits](ACCOUNTS_PASSPORTS.md).

Bangla/English goal intake now collects chosen location precision, growing space,
sunlight and available soil/season details. Optional Android voice returns editable
text. Deterministic rules return eligible reviewed profiles with reasons and
uncertainty, or explain missing/unsupported data. Goals are transient, not stored.
Tests cover unsupported regions, missing soil, mismatches and empty results.
Actual approved content remains pending; no demo/draft recommendation fallback or
LLM care generation exists. See [scope and privacy](GOALS_RECOMMENDATIONS.md).

Reviewed directive-based care plans now provide bilingual dated instructions,
citations/review dates, explicit missing/conflicting guidance and private immutable
versions. Saving retains structured conditions, not free goal/soil prose. Evidence
changes withhold old advice. Approved care content, weather quests and LLM providers
remain pending. See [implemented care scope](CARE_PLANS.md).
