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

The catalog is explicitly demo-only. It is useful for checking the phone → API → database path. It must not be used for planting decisions.

## First real product slice

Allow a user to enter a goal, district or approximate area, growing space, sunlight, and available soil information. Return only reviewed species with an explanation of suitability and uncertainty. A recommendation is complete only when tests cover unsupported regions, missing soil detail, and an empty result.
