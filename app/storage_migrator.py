import requests
import json
import streamlit as st


def export_storage_metadata(BASE, TOKEN):
    st.write('Exporting Storage metadata...')
    HEAD = {'X-StorageApi-Token': TOKEN}

    # Get all buckets in project
    buckets_response = requests.get(url=f'{BASE}v2/storage/buckets?include=include', headers=HEAD)
    buckets_data = buckets_response.json()
    st.write('Buckets exported...')
    # Filter out buckets
    buckets_to_migrate = [b for b in buckets_data if not b['isReadOnly']]

    # Write bucket details to json file
    # buckets_path = f'buckets_{TOKEN.split("-")[0]}.json'
    # with open(buckets_path, "w") as f:
    #     json.dump(buckets_to_migrate, f)

    # Get all tables from all buckets
    tables_to_migrate = []
    st.write('Proceeding to export tables...')
    for bucket in buckets_to_migrate:
        bucket_id = bucket['id']
        tables_response = requests.get(url=f'{BASE}v2/storage/buckets/{bucket_id}/tables', headers=HEAD)
        tables_data = tables_response.json()
        tables_to_migrate.extend(tables_data)

    # Get table metadata
    tables_to_migrate_metadata = []
    for table in tables_to_migrate:
        table_id = table['id']
        tables_metadata_response = requests.get(url=f'{BASE}v2/storage/tables/{table_id}', headers=HEAD)
        if tables_metadata_response.status_code not in [200, 202]:
            print(tables_metadata_response.status_code)
            break
        tables_to_migrate_metadata.append(tables_metadata_response.json())
    
    st.write('Tables exported...')
    # Write table details to json file
    # tables_path = f'tables_{TOKEN.split("-")[0]}.json'
    # with open(tables_path, "w") as f:
    #     json.dump(tables_to_migrate_metadata, f)
    return buckets_to_migrate, tables_to_migrate_metadata

def migrate_buckets(BASE, TOKEN, BUCKETS, BUCKET_IDS_SELECTION = None):
    HEAD = {'X-StorageApi-Token': TOKEN}

    # Read buckets data from file
    buckets = BUCKETS
    selected_buckets = []

    if BUCKET_IDS_SELECTION:
        for bucket in buckets:
            if bucket['id'] in BUCKET_IDS_SELECTION:
                selected_buckets.append(bucket)
    else:
        for bucket in buckets:
            selected_buckets.append(bucket)

    
    for bucket in selected_buckets:        
        values = {
            "name": bucket['id'].split('.c-')[-1],
            "stage": bucket['stage'],
            "description": bucket['description']
        }
        if bucket['id'].split('.c-')[-1] != bucket['displayName']:
            st.write('Creating bucket', bucket['id'], '.', 'Display name is', bucket['displayName'], '.', 'Creating bucket and updating display name!')
            new_bucket = requests.post(url=f'{BASE}v2/storage/buckets', headers=HEAD, json=values)
            if new_bucket.status_code == 201:
                payload = {'displayName': bucket['displayName']}
                update_bucket = requests.put(url=f"{BASE}v2/storage/buckets/{bucket['id']}", headers=HEAD, data=payload)
                if update_bucket.status_code != 200:
                    st.write('Failed to update display name:', update_bucket.status_code, new_bucket.text)
            else:
                st.write('Failed to create bucket:', new_bucket.status_code, new_bucket.text)
        else:
            st.write('Creating bucket', bucket['id'], '.')
            new_bucket = requests.post(url=f'{BASE}v2/storage/buckets', headers=HEAD, json=values)
            if new_bucket.status_code != 201:
                st.write('Failed to create bucket:', new_bucket.status_code, new_bucket.text)

def migrate_tables(BASE, TOKEN, TABLES, BUCKET_IDS_SELECTION = None):
    HEAD = {'X-StorageApi-Token': TOKEN}
    fails = []

    selected_tables = []

    if BUCKET_IDS_SELECTION:
        for table in TABLES:
            bucket_id = '.'.join(table['id'].split('.')[:2])
            if bucket_id in BUCKET_IDS_SELECTION:
                selected_tables.append(table)
    else:
        for table in TABLES:
            selected_tables.append(table)

    for table in selected_tables:
        bucket_id = '.'.join(table['id'].split('.')[:2])
        values = {
            "name": table['name'],
            "primaryKeysNames": table['primaryKey'],
            "columns": [{"name": c} for c in table['columns']]
        }

        try:
            # Create table
            new_table = requests.post(url=f'{BASE}v2/storage/buckets/{bucket_id}/tables-definition',
                                      headers=HEAD,
                                      json=values)
            if new_table.status_code != 202:
                st.write('FAILED table:', table['name'])
                fails.append([table, new_table.text])
            else:
                st.write('Created table:', table['name'])
        except Exception as e:
            st.write('FAILED table:', table['name'], str(e))
            fails.append(table)

    return fails

def migrate_tables_native_types(BASE, TOKEN, TABLES, BUCKET_IDS_SELECTION = None):
    HEAD = {'X-StorageApi-Token': TOKEN}
    fails = []

    selected_tables = []

    if BUCKET_IDS_SELECTION:
        for table in TABLES:
            bucket_id = '.'.join(table['id'].split('.')[:2])
            if bucket_id in BUCKET_IDS_SELECTION:
                selected_tables.append(table)
    else:
        for table in TABLES:
            selected_tables.append(table)                
                
    # Create tables in destination project
    for t in selected_tables:
        bucket_id = '.'.join(t['id'].split('.')[:2])   
        
        values = {
        "name": t['name'],
        "primaryKeysNames": t['primaryKey'],
        "columns": []
        }
        try:
            if 'columnMetadata' in t and len(t['columnMetadata'])>0:
                st.write('Table', t['name'], 'will be created with defined data types...')
                for c in t['columns']: 
                    metadata = t['columnMetadata'].get(c, [])  # Get metadata for the current column, or an empty list if not found
                    nullable = False
                    length = False
                    basetype = 'STRING'
                    for m in metadata:
                        if m['key'] == 'KBC.datatype.basetype':
                            basetype = m['value']
                        elif m['key'] == 'KBC.datatype.length':
                            length = m['value']
                        elif m['key'] == 'KBC.datatype.nullable':
                            if m['value'] == '1':
                                nullable = True
                            else:
                                nullable = False
                    
                    if c in t['primaryKey']:
                        nullable = False

                    if length:
                        new_column = {"name": c, "definition": {"type": basetype, "nullable": nullable, "length": length}}
                    else:
                        new_column = {"name": c, "definition": {"type": basetype, "nullable": nullable}}

                    values['columns'].append(new_column)
            else:
                st.write('Table', t['name'], 'is not a Native Types table on the source - it will be created with Varchar MAX types...')
                for c in t['columns']:
                    new_column={"name":c} 
                    values['columns'].append(new_column)
            
            #Create table
            new_table = requests.post(url=''.join([BASE, 'v2/storage/buckets/', bucket_id, '/tables-definition']),
                                      headers = HEAD,
                                      json = values)

            if new_table.status_code != 202:
                st.write('Table failed:', t['name'])
                fails.append([t, new_table.text])
            else:
                st.write('Table created:', t['name'])
        except Exception as e:
            st.write('Table failed:', t['name'], str(e))
            fails.append(t)                