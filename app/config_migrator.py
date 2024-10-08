import requests
import streamlit as st
import datetime
import concurrent.futures
import csv


def get_keboola_configs(BASE, HEAD, skip=None, keep=None, selected_configs=None):
    configs_src = []
    
    if selected_configs:
        for config in selected_configs:
            component_id = config[0]
            configuration_id = config[2]
            configs = requests.get(f'{BASE}v2/storage/components/{component_id}/configs/{configuration_id}', headers=HEAD)
            config_out = configs.json()
            config_out['component_id'] = component_id
            configs_src.append(config_out)

    else:
        components_src = requests.get(f'{BASE}v2/storage/components', headers=HEAD)
        for component in components_src.json():
            component_id = component['id']
            if skip and component_id in skip:
                st.write(f'Component {component_id} is skipped...')
                continue
                
            if keep and component_id not in keep:
                # st.write(f'Component {component_id} is skipped...')
                continue
            
            configs = requests.get(f'{BASE}v2/storage/components/{component_id}/configs', headers=HEAD)
            for config in configs.json():
                config['component_id'] = component_id
                configs_src.append(config)

    
    return configs_src

def get_component_ids(BASE, HEAD):
    components_src = requests.get(f'{BASE}v2/storage/components', headers=HEAD)
    component_ids = []

    for component in components_src.json():
        component_id = component['id']
        component_ids.append(component_id)
    
    component_ids = list(set(component_ids))
        
    return component_ids

def get_component_configurations(BASE, HEAD, COMPONENT_IDS=None, MODE=None):
    configs_src = []
    if COMPONENT_IDS and len(COMPONENT_IDS) > 0:
        if MODE == 'keep':
            for component_id in COMPONENT_IDS:
                configs = requests.get(f'{BASE}v2/storage/components/{component_id}/configs', headers=HEAD)
                for config in configs.json():
                    configs_src.append([component_id, config['name'], config['id']])
        elif MODE == 'skip':
            components_src = requests.get(f'{BASE}v2/storage/components', headers=HEAD)
            for component in components_src.json():
                if component['id'] not in COMPONENT_IDS:
                    component_id = component['id']
                    configs = requests.get(f'{BASE}v2/storage/components/{component_id}/configs', headers=HEAD)
                    for config in configs.json():
                        configs_src.append([component_id, config['name'], config['id']])
    else:
        components_src = requests.get(f'{BASE}v2/storage/components', headers=HEAD)
        for component in components_src.json():
            component_id = component['id'] 
            configs = requests.get(f'{BASE}v2/storage/components/{component_id}/configs', headers=HEAD)
            for config in configs.json():
                configs_src.append([component_id, config['name'], config['id']])
    return configs_src

def migrate_config(config, BASE, HEAD, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, source_name, destination_name, DEBUG=False):
    log_messages = []
    CSV_PATH = 'log.csv'
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

        metadataFolderPayloadPython = False
        if componentId == 'keboola.python-transformation-v2':
            python_metadata = requests.get(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/keboola.python-transformation-v2/configs/{configurationId}/metadata',
                                              headers=HEAD)
            if python_metadata.json():
                metadataFolderPayloadPython = {
                    "metadata[0][key]": "KBC.configuration.folderName",
                    "metadata[0][value]": python_metadata.json()[0]['value']
                }

        if not DEBUG:
            config_dest = requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/{componentId}/configs',
                                        headers=HEAD_DEST,
                                        json=values)
            if config_dest.status_code != 201:
                response = requests.put(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/{componentId}/configs/{configurationId}',
                                                  headers=HEAD_DEST,
                                                  json=values)
                if response.status_code != 200:
                    raise Exception(f'Failed to update config: {response.text}')

            if metadataFolderPayload:
                requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/keboola.snowflake-transformation/configs/{configurationId}/metadata',
                              headers=HEAD_FORM_DEST,
                              data=metadataFolderPayload)

            if metadataFolderPayloadPython:
                requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/keboola.python-transformation-v2/configs/{configurationId}/metadata',
                              headers=HEAD_FORM_DEST,
                              data=metadataFolderPayloadPython)

            current_time = datetime.datetime.now().replace(microsecond=0)
            log_message = f"**Migrated**: {config['component_id']} **{config['name']}** at {current_time}"
            log_messages.append(log_message)

        with open(CSV_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([config['component_id'], source_name, destination_name, config['id'], config['name'], current_time, 'Success', log_message])


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
                    config_dest_row = requests.post(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/{componentId}/configs/{configurationId}/rows/{rowId}',
                                                    headers=HEAD_DEST,
                                                    json=values_row)
                    config_dest_row_update = requests.put(f'{BASE}v2/storage/branch/{BRANCH_DEST}/components/{componentId}/configs/{configurationId}/rows/{rowId}',
                                                    headers=HEAD_DEST,
                                                    json=values_row)
                #log_messages.append(config_dest_row_update.json())




    except Exception as e:
        current_time = datetime.datetime.now().replace(microsecond=0)
        log_message = f'FAILED: {config["component_id"]} {config["name"]} {str(e)}'
        log_messages.append(log_message)

        with open(CSV_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([config['component_id'], source_name, destination_name, config['id'], config['name'], current_time, 'Failed', log_message])

        return (False, log_messages)
    
    return (True, log_messages)

def migrate_configs(BASE, HEAD, configs_src, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, source_name, destination_name, DEBUG=False):
    fails = []
    log_messages = []
    
    st.write(f'Proceeding to migrate {len(configs_src)} configurations...')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(migrate_config, config, BASE, HEAD, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, source_name, destination_name, DEBUG): config for config in configs_src}

        for future in concurrent.futures.as_completed(futures):
            config = futures[future]
            try:
                success, messages = future.result()
                log_messages.extend(messages)
                if not success:
                    fails.append(config)
            except Exception as exc:
                log_messages.append(f'FAILED: {config["component_id"]} {config["name"]} {str(exc)}')
                fails.append(config)

    for message in log_messages:
        st.write(message)

    return fails