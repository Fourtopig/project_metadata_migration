import streamlit as st
import re
import json
import os
from requests.exceptions import ConnectionError, Timeout
from config_migrator import get_keboola_configs, migrate_configs, get_component_ids, get_component_configurations

def main():
    st.title("Project Metadata Migration")

    include_shared_code = False

    # Set the working directory to the directory where the script is located.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Check if the source file exists
    source_config_path = 'config_source.json'
    destination_config_path = 'config_destination.json'

    # Load source config
    if 'source_config' not in st.session_state:
        if os.path.exists(source_config_path):
            with open(source_config_path, 'r') as file:
                st.session_state.source_config = json.load(file)
        else:
            st.write(f"Source config file not found: {source_config_path}")
            return
    source_config = st.session_state.source_config

    # Load destination config
    if 'destination_config' not in st.session_state:
        if os.path.exists(destination_config_path):
            with open(destination_config_path, 'r') as file:
                st.session_state.destination_config = json.load(file)
        else:
            st.write(f"Destination config file not found: {destination_config_path}")
            return
    destination_config = st.session_state.destination_config

    # General settings in the sidebar
    st.sidebar.title("General Settings")

    # Get the list of project names from the source config
    all_source_project_names = [project['name'] for project in source_config['projects']]

    # User selection of source project in the sidebar
    source_selected_project = st.sidebar.selectbox("Select Source Project", all_source_project_names)
    source_selected_project_details = [project for project in source_config['projects'] if project['name'] == source_selected_project]

    source_api_token = source_selected_project_details[0]['token']
    source_project_host = source_selected_project_details[0]['url']

    # Get the list of project names from the destination config
    all_destination_project_names = [project['name'] for project in destination_config['projects']]

    # User selection of destination projects in the sidebar
    destination_selected_projects = st.sidebar.multiselect("Select Destination Projects", all_destination_project_names)
    destination_selected_project_details = [project for project in destination_config['projects'] if project['name'] in destination_selected_projects]
    dest_project_names = [project['name'] for project in destination_selected_project_details]
    dest_project_names_str = ", ".join([f"**{name}**" for name in dest_project_names])

    if source_selected_project_details:
        st.markdown(f"The source project from which the configuration will be migrated: **{source_selected_project_details[0]['name']}**")

    if dest_project_names_str:
        st.markdown(f"The selected configurations will be migrated to: {dest_project_names_str}")

    if source_project_host and source_api_token and destination_selected_project_details:
        HEAD = {'X-StorageApi-Token': source_api_token}
        HEAD_FORM = {'X-StorageApi-Token': source_api_token, 'Content-Type': 'application/x-www-form-urlencoded'}
        # Migrate Configurations in the main area
        st.subheader("Migrate Configurations")
        st.markdown("All components will be migrated unless you select 'Keep' or 'Skip' to only migrate or skip selected Component IDs. Select an option in the process settings from the left panel.")
        st.sidebar.title("Process Settings")
        processing_detail = st.sidebar.selectbox("Processing Detail", ["", "Keep", "Skip"])
        
        # Load available component options only once
        if 'available_component_options' not in st.session_state:
            with st.spinner("Fetching available components..."):
                st.session_state.available_component_options = get_component_ids(source_project_host, {'X-StorageApi-Token':source_api_token})
        available_component_options = st.session_state.available_component_options

        component_ids = []
        shared_code_ids_snowflake = []
        shared_code_ids_python = []

        if processing_detail:
            ignoreflow = st.sidebar.checkbox("Include orchestrator and scheduler", value=False)
            # Remove orchestrators and schedulers from components
            if ignoreflow:
                component_options = available_component_options
            else:
                component_to_remove = ["keboola.scheduler", "keboola.orchestrator"]
                component_options = [item for item in available_component_options if item not in component_to_remove]

            if processing_detail == "Keep":
                st.markdown("Select Component IDs you want to keep (migrate).")
            elif processing_detail == "Skip":
                st.markdown("Select Component IDs you want to skip (not migrate).")
            component_ids = st.multiselect("Component IDs", component_options)

        skip = None
        keep = None
        if processing_detail == 'Skip':
            skip = component_ids
            only_selected_configs = st.checkbox("Select individual configurations you want to skip.", value=False)

        elif processing_detail == 'Keep':
            keep = component_ids
            only_selected_configs = st.checkbox("Select individual configurations or configurations based on the source system.", value=False)
        else:
            only_selected_configs = ''

        if only_selected_configs:
            configuration_options = None
            with st.spinner("Fetching configurations..."):
                if skip:
                    st.write('Fetching available configurations besides the components you wanted to skip...')
                    configuration_options = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, component_ids, 'skip')
                elif keep:
                    st.write('Fetching available configurations for components you selected...')
                    configuration_options = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, component_ids, 'keep')
                else:
                    st.write('Fetching available configurations for all components...')
                    configuration_options = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, None, 'all')

            # Remove orchestrators and schedulers from configurations
            components_to_ignore = [] if ignoreflow else ["keboola.scheduler", "keboola.orchestrator"]
            selected_configuration_options = [item for item in configuration_options if item[0] not in components_to_ignore]

            # Selects configurations according to the user's choice
            if selected_configuration_options and processing_detail == "Keep":
                st.write("Select a Migrate whole [Folder] or [Type] to choose component configurations related to the selected folder in Keboola. Or Migrate specific components for a free selection of configurations.")
                select_options = st.selectbox("Select option:", ["Migrate whole [Folder] or [Type]", "Migrate specific components"])
                if select_options == "Migrate specific components":
                    st.write("Select Component IDs, keep empty for all.")
                    configuration_ids = st.multiselect("Configuration IDs", selected_configuration_options)
 
                elif select_options == "Migrate whole [Folder] or [Type]":
                    options = list({re.search(r'\[(.*?)\]', item[1]).group(1) for item in selected_configuration_options if "[" in item[1] and "]" in item[1]})
                    selected_options = st.multiselect('[Folder] or [Type]:', options)
 
                    filtered_data = [item for item in selected_configuration_options if any(selected in item[1] for selected in selected_options)]
                    st.write("Select Component IDs, keep empty for all.")
                    selected_configuration_ids = st.multiselect("Configuration IDs:", filtered_data)
 
                    if selected_configuration_ids:
                        configuration_ids = selected_configuration_ids 
                    else:
                        configuration_ids = filtered_data

            elif selected_configuration_options and processing_detail == "Skip":
                selected_configuration_ids = st.multiselect("Configuration IDs, keep empty for all.", selected_configuration_options)

                if selected_configuration_ids:
                    configuration_ids =  [item for item in selected_configuration_options if item not in selected_configuration_ids]
                else:
                    configuration_ids = selected_configuration_options

            # Adds variables related to the selected transformation
            include_variable = st.sidebar.checkbox("Include migration of variables related to selected transformations (Python and Snowflake)", value=True)
            if include_variable:
                all_variables_ids = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, ["keboola.variables"], 'keep')
                variables_ids = []

                for config in configuration_ids:
                    config_id = config[2] 
                    match_found = False

                    for variable in all_variables_ids:
                        variable_definition = variable[1]  

                        if variable_definition.endswith(config_id):
                            match_found = True
                            variables_ids.append(variable) 

                configuration_ids.extend(variables_ids)

            # Adds variables related to the selected transformation
            include_shared_code = st.sidebar.checkbox("Include shared codes related to selected transformations (Python and Snowflake)", value=True)
            if include_shared_code:
                shared_codes = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, ["keboola.shared-code"], 'keep')
                shared_code_configs = get_keboola_configs(source_project_host, HEAD, skip, keep, shared_codes)

        # Initialize session state for the first button
        if 'config_loaded' not in st.session_state:
            st.session_state['config_loaded'] = False

        # First button
        if st.button("Load Configurations"):
            with st.spinner("Loading configurations..."):
                if only_selected_configs and len(configuration_ids) > 0:
                    configs = get_keboola_configs(source_project_host, HEAD, skip, keep, configuration_ids)
                else:
                    configs = get_keboola_configs(source_project_host, HEAD, skip, keep)

                st.write("Configurations to migrate:")
                # Display the loaded configurations

                # Store shared_code_ids in session state
                st.session_state.shared_code_ids_snowflake = []
                st.session_state.shared_code_ids_python = []
             
                for config in configs:
                    component_id = config.get("component_id")
                    name = config.get("name")
                    config_id = config.get("id")
        
                    st.write(f"**{component_id}** name **{name}** and ID **{config_id}**")
 
                    if include_shared_code:
                        # Select shared_code for Python and Snowflake transforamtion
                        if config.get('component_id') == "keboola.snowflake-transformation":
                            configuration = config.get('configuration', {})
                            shared_code_row_ids = configuration.get('shared_code_row_ids', [])
                            if shared_code_row_ids:
                                st.session_state.shared_code_ids_snowflake.extend(shared_code_row_ids)

                        elif config.get('component_id') == "keboola.python-transformation-v2":
                            configuration = config.get('configuration', {})
                            shared_code_row_ids = configuration.get('shared_code_row_ids', [])
                            if shared_code_row_ids:
                                st.session_state.shared_code_ids_python.extend(shared_code_row_ids)

                if include_shared_code:
                    st.write("Shared code for selected **Python and Snowflake transformations** will also be migrated")
              
                st.write("")
                st.write("Clicking on button **Migrate Configurations** will migrate the following configurations. Click on **Dismiss Configurations** to clear the configuration selection")
                # Set the state after configurations are loaded
                st.session_state['config_loaded'] = True

        # Second button, which appears only after the configurations are loaded
        if st.session_state['config_loaded']:
            # Ensure the migrate_clicked state is initialized
            if 'migrate_clicked' not in st.session_state:
                st.session_state['migrate_clicked'] = False
    
            # Display buttons only if migrate_clicked is False
            if not st.session_state['migrate_clicked']:
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col1:
                    migrate_clicked = st.button("Migrate Configurations")
                
                with col2:
                    if st.button("Dismiss Configurations"):
                        # Reset the session state to its initial state
                        st.session_state.clear()
                        st.experimental_rerun()

                # If "Migrate Configurations" is clicked, update state and rerun
                if migrate_clicked:
                    st.session_state['migrate_clicked'] = True
    
            if st.session_state['migrate_clicked']:
                total_projects = len(destination_selected_project_details)
                st.subheader("Migration Progress")
                percent_complete_text = st.empty()  # Placeholder for dynamic status text
                percent_complete_text.text("0 %")

                progress_bar = st.progress(0)
                status_text = st.empty()  # Placeholder for dynamic status text

                for i, dest_project in enumerate(destination_selected_project_details):
                    destination_api_token = dest_project['token']
                    destination_project_name = dest_project['name']

                    # Update status text to show the current project being migrated
                    status_text.text(f"Migrating project {i + 1} of {total_projects}: {destination_project_name}")

                    # Execute migrate configurations script for all selected projects
                    HEAD = {'X-StorageApi-Token':source_api_token}
                    HEAD_FORM = {'X-StorageApi-Token':source_api_token, 'Content-Type': 'application/x-www-form-urlencoded'}
                    HEAD_DEST = {'X-StorageApi-Token':destination_api_token}
                    HEAD_FORM_DEST = {'X-StorageApi-Token':destination_api_token, 'Content-Type': 'application/x-www-form-urlencoded'}
                    BRANCH_DEST = 'default'

                    st.subheader(f"The configuration migration to the {destination_project_name} project is in progress")
                    
                    # Retrieve shared_code_ids from session state
                    shared_code_ids_snowflake = st.session_state.get('shared_code_ids_snowflake', [])
                    shared_code_ids_python = st.session_state.get('shared_code_ids_python', [])

                    try:
                        if only_selected_configs and len(configuration_ids) > 0:
                            configs = get_keboola_configs(source_project_host, HEAD, skip, keep, configuration_ids)
                            if include_shared_code:
                                for shared_code in shared_code_configs:
                                    if shared_code["id"] == "shared-codes.python-transformation-v2":
                                        shared_code["rows"] = [row for row in shared_code["rows"] if row["id"] in shared_code_ids_python]
                                    elif shared_code["id"] == "shared-codes.snowflake-transformation":
                                        shared_code["rows"] = [row for row in shared_code["rows"] if row["id"] in shared_code_ids_snowflake]

                                #st.write(shared_code_configs)
                                migrate_shared_code = migrate_configs(source_project_host, HEAD, shared_code_configs, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, DEBUG=False)

                        else:
                            configs = get_keboola_configs(source_project_host, HEAD, skip, keep)
                        
                        fails = migrate_configs(source_project_host, HEAD, configs, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, DEBUG=False)
                        st.write(f"Migration to {destination_project_name} completed. Failures:", fails)

                    except (ConnectionError, Timeout) as conn_err:
                        st.warning(f"Connection error occurred while migrating to {destination_project_name}. Please check your internet connection and try again.")
                        st.error(f"Error details: {conn_err}")
                    except Exception as e:
                        st.warning(f"Something went wrong with the migration to {destination_project_name}. Please try again later.")
                        st.error(f"Error details: {e}")

                    # Update progress bar and percentage text after completing each project
                    percent_complete = int(((i + 1) / total_projects) * 100)
                    percent_complete_text.text(f"{percent_complete} %")
                    progress_bar.progress((i + 1) / total_projects)

                # Final status update after all migrations are complete
                status_text.text("Migration completed!")
                if fails == []:
                    st.balloons()

                st.session_state['migrate_clicked'] = False
                st.session_state['config_loaded'] = False
    else:
        st.markdown("First, select the source project from which you want to transfer the configuration. Then, choose the projects to which you want to migrate it...")

if __name__ == "__main__":
    main()
