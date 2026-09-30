-- Illustrative UI/API data. These rows are NOT suitability or care advice.
INSERT INTO catalog_source (id, title, review_status)
VALUES ('starter-samples', 'Starter sample data (unverified)', 'demo');

INSERT INTO species (
    id, common_name_en, common_name_bn, category, source_id
) VALUES
    ('demo-neem', 'Neem', 'নিম', 'tree', 'starter-samples'),
    ('demo-okra', 'Okra', 'ঢেঁড়স', 'crop', 'starter-samples');
