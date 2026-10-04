"""Offline validation by default; explicit atomic, append-only catalog import."""
import argparse
import hashlib
import json
import os
import sys

from pydantic import ValidationError
import sqlalchemy as sa

from app.catalog_bundle import CatalogBundle, read_bundle
from app.migrations import migration_connection, require_head


def import_bundle(bundle: CatalogBundle, database_url: str):
    # Revalidate even when called directly, not only through the JSON reader.
    bundle = CatalogBundle.model_validate(bundle.model_dump(mode='json'))
    manifest = bundle.model_dump(mode='json')
    # Preserve schema-v1 manifest hashes imported before care_guidance existed.
    for plant in manifest['plants']:
        for profile in plant['profiles']:
            if not profile['care_guidance']:
                profile.pop('care_guidance')
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    with migration_connection(database_url) as connection:
        require_head(connection)
        prior = connection.execute(sa.text('SELECT sha256 FROM public.catalog_import WHERE bundle_id=:id'), {'id': bundle.bundle_id}).scalar_one_or_none()
        if prior:
            if prior != digest:
                raise RuntimeError('Bundle ID already imported with different content; create a new version')
            return {'sha256': digest, 'already_imported': True}
        # Any identity collision refuses the entire transaction; never upsert over
        # user-edited names, reviewed permissions, dates or inactive flags.
        connection.execute(sa.text('INSERT INTO public.catalog_import (sha256,bundle_id,manifest) VALUES (:hash,:id,CAST(:manifest AS jsonb))'),
                           {'hash': digest, 'id': bundle.bundle_id, 'manifest': canonical})
        for source in bundle.sources:
            values = source.model_dump()
            columns = ','.join(values)
            placeholders = ','.join(':' + key for key in values)
            connection.execute(sa.text(f'INSERT INTO public.catalog_source ({columns}) VALUES ({placeholders})'), values)
        for plant in bundle.plants:
            connection.execute(sa.text('''INSERT INTO public.species
                (id,common_name_en,common_name_bn,scientific_name,category,source_id)
                VALUES (:id,:common_name_en,:common_name_bn,:scientific_name,:category,:source_id)'''),
                plant.model_dump(exclude={'profiles'}))
            for profile in plant.profiles:
                values = profile.model_dump(exclude={'requirements', 'care_guidance'})
                values.update(species_id=plant.id, import_sha256=digest)
                columns = ','.join(values)
                placeholders = ','.join(':' + key for key in values)
                connection.execute(sa.text(f'INSERT INTO public.plant_profile ({columns}) VALUES ({placeholders})'), values)
                for requirement in profile.requirements:
                    values = requirement.model_dump()
                    values.update(profile_id=profile.id, value=json.dumps(values['value'], ensure_ascii=False))
                    connection.execute(sa.text('''INSERT INTO public.plant_requirement
                        (profile_id,key,value,source_id,source_locator,interpretation_note)
                        VALUES (:profile_id,:key,CAST(:value AS jsonb),:source_id,:source_locator,:interpretation_note)'''), values)
                for guidance in profile.care_guidance:
                    values = guidance.model_dump()
                    values['profile_id'] = profile.id
                    columns = ','.join(values)
                    placeholders = ','.join(':' + key for key in values)
                    connection.execute(sa.text(f'INSERT INTO public.plant_care_guidance ({columns}) VALUES ({placeholders})'), values)
    return {'sha256': digest, 'already_imported': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm', action='store_true')
    args = parser.parse_args(argv)
    if args.apply and not args.confirm:
        parser.error('--apply requires --confirm after backup and content/rights review')
    try:
        bundle = read_bundle(args.path)
        if args.apply:
            result = import_bundle(bundle, os.environ.get('DATABASE_URL', ''))
            print(json.dumps(result))
        else:
            print(f'VALID: {len(bundle.sources)} sources, {len(bundle.plants)} plants; no database writes. Validation does not grant reuse or agronomic approval.')
    except ValidationError as exc:
        # Never echo the supplied input values (URLs may contain secrets).
        print(f'Catalog validation failed ({exc.error_count()} errors); inspect the local bundle against the documented format.', file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print('Catalog file invalid or unreadable; no import committed.', file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f'Catalog import failed ({type(exc).__name__}); transaction rolled back.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
