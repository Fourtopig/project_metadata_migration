import requests
import streamlit as st

def get_keboola_configs(BASE, HEAD, skip=None, keep=None):
    st.write('Exporting configurations...')
    components_src = requests.get(f'{BASE}v2/storage/components', headers=HEAD)
    configs_src = []

    for component in components_src.json():
        component_id = component['id']
        if skip and component_id in skip:
            st.write(f'Component {component_id} is skipped...')
            continue
            
        if keep and component_id not in keep:
            st.write(f'Component {component_id} is skipped...')
            continue

        configs = requests.get(f'{BASE}v2/storage/components/{component_id}/configs', headers=HEAD)
        for config in configs.json():
            config['component_id'] = component_id
            configs_src.append(config)

    st.write(f'Configurations extracted... ')
    return configs_src

def get_component_ids(BASE, HEAD):
    components_src = requests.get(f'{BASE}v2/storage/components', headers=HEAD)
    component_ids = []

    for component in components_src.json():
        component_id = component['id']
        component_ids.append(component_id)
    
    component_ids = list(set(component_ids))
        
    return component_ids

def migrate_configs(BASE, HEAD, configs_src, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, DEBUG=False):
    fails = []
    st.write(f'Proceeding to migrate {len(configs_src)} configurations...')
    for config in configs_src:
        try:
            configurationId = config['id']
            configurationName = config['name']
            configurationConfig = config['configuration']
            componentId = config['component_id']
            configurationDescription = config['description']

            values = {
                'configurationId': configurationId,
                'name': configurationName,
                'configuration': configurationConfig
            }
            if configurationDescription:
                values['description'] = configurationDescription

            metadataFolderPayload = False
            if componentId == 'keboola.snowflake-transformation':
                snowflake_metadata = requests.get(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/keboola.snowflake-transformation/configs/{configurationId}/metadata',
                                                  headers=HEAD)
                if snowflake_metadata.json():
                    metadataFolderPayload = {
                        "metadata[0][key]": "KBC.configuration.folderName",
                        "metadata[0][value]": snowflake_metadata.json()[0]['value']
                    }
                
            if not DEBUG:
                config_dest = requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/{componentId}/configs',
                                            headers=HEAD_DEST,
                                            json=values)

                if metadataFolderPayload:
                    requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/keboola.snowflake-transformation/configs/{configurationId}/metadata',
                                  headers=HEAD_FORM_DEST,
                                  data=metadataFolderPayload)

            for row in config['rows']:
                rowId = row['id']
                rowName = row['name']
                rowConfig = row['configuration']
                rowDescription = row['description']
                values_row = {
                    'rowId': rowId,
                    'name': rowName,
                    'configuration': rowConfig
                }
                if rowDescription:
                    values_row['description'] = rowDescription
                
                if not DEBUG:
                    config_dest_row = requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/{componentId}/configs/{config_dest.json()["id"]}/rows',
                                                    headers=HEAD_DEST,
                                                    json=values_row)

            st.write('Migrated:', config['component_id'], config['name'])
        except Exception as e:
            print('FAILED:', config['component_id'], config['name'], str(e))
            fails.append(config)

    return fails
