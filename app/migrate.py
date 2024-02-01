import streamlit as st
from config_migrator import get_keboola_configs, migrate_configs, get_component_ids, get_component_configurations
from storage_migrator import export_storage_metadata, migrate_buckets, migrate_tables, migrate_tables_native_types

def main():
    st.title("Project Metadata Migration")

    # General settings in the sidebar
    st.sidebar.title("General Settings")
    source_project_host = st.sidebar.selectbox("Source Project Host",
                                               ["https://connection.keboola.com/",
                                                "https://connection.eu-central-1.keboola.com/",
                                                "https://connection.north-europe.azure.keboola.com/",
                                                "Others (Enter custom hostname)"])
    if source_project_host == "Others (Enter custom hostname)":
        source_project_host = st.sidebar.text_input("Enter Custom Source Hostname")

    same_as_source = st.sidebar.checkbox("Destination host same as Source", value=False)
    if same_as_source:
        destination_project_host = source_project_host
    else:
        destination_project_host = st.sidebar.selectbox("Destination Project Host",
                                                        ["https://connection.keboola.com/",
                                                         "https://connection.eu-central-1.keboola.com/",
                                                         "https://connection.north-europe.azure.keboola.com/",
                                                         "Others (Enter custom hostname)"])
        if destination_project_host == "Others (Enter custom hostname)":
            destination_project_host = st.sidebar.text_input("Enter Custom Destination Hostname")

    source_api_token = st.sidebar.text_input("Source Project Storage API Token", type="password")
    destination_api_token = st.sidebar.text_input("Destination Project Storage API Token", type="password")

    # MAIN CODE 
    st.header("Migrate Configurations")
    if source_project_host and source_api_token and destination_project_host and destination_api_token:
        # Migrate Configurations in the main area
        st.markdown("All components will be migrated unless you select 'Keep' or 'Skip' to only migrate or skip selected Component IDs.")
        processing_detail = st.selectbox("Processing Detail", ["", "Keep", "Skip"])
        component_options = get_component_ids(source_project_host, {'X-StorageApi-Token':source_api_token})
        component_ids = []
        if processing_detail:
            if processing_detail == "Keep":
                st.markdown("Select Component IDs you want to keep (migrate)")
            elif processing_detail == "Skip":
                st.markdown("Select Component IDs you want to skip (not migrate)")
            component_ids = st.multiselect("Component IDs", component_options)

        skip = None
        keep = None
        if processing_detail == 'Skip':
            skip = component_ids
        elif processing_detail == 'Keep':
            keep = component_ids

        only_selected_configs = st.checkbox("Migrate only particular configurations", value=False)

        if only_selected_configs:
            configuration_options = None
            if skip:
                st.write('Fetching available configurations besides the components you wanted to skip...')
                configuration_options = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, component_ids, 'skip')
            elif keep:
                st.write('Fetching available configurations for components you selected...')
                configuration_options = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, component_ids, 'keep')
            else:
                st.write('Fetching available configurations for all components...')
                configuration_options = get_component_configurations(source_project_host, {'X-StorageApi-Token':source_api_token}, None, 'all')

            if configuration_options:
                configuration_ids = st.multiselect("Configuration IDs", configuration_options)

        if st.button("Migrate Configurations"):
            # Execute migrate configurations script
            HEAD = {'X-StorageApi-Token':source_api_token}
            HEAD_FORM = {'X-StorageApi-Token':source_api_token, 'Content-Type': 'application/x-www-form-urlencoded'}
            HEAD_DEST = {'X-StorageApi-Token':destination_api_token}
            HEAD_FORM_DEST = {'X-StorageApi-Token':destination_api_token, 'Content-Type': 'application/x-www-form-urlencoded'}
            BRANCH_DEST = 'default'

            

            if only_selected_configs and len(configuration_ids)>0:
                configs = get_keboola_configs(source_project_host, HEAD, skip, keep, configuration_ids)
            else:
                configs = get_keboola_configs(source_project_host, HEAD, skip, keep)
            
            fails = migrate_configs(source_project_host, HEAD, configs, HEAD_DEST, HEAD_FORM_DEST, BRANCH_DEST, DEBUG=False)
            
            st.write("Migration completed. Failures:", fails)

        # Migrate Storage Object Definitions in the main area
        st.header("Migrate Storage Object Definitions")
        native_data_types = st.checkbox("Destination project should use Native Data Types", value=False)

        if st.button("Migrate Storage Object Definitions"):
            # Execute migrate storage object definitions script
            if not native_data_types:
                buckets_to_migrate, tables_to_migrate = export_storage_metadata(source_project_host, source_api_token)
                migrate_buckets(destination_project_host, destination_api_token, buckets_to_migrate)
                migrate_tables(destination_project_host, destination_api_token, tables_to_migrate)
                st.write("Migration completed.")
            else: 
                buckets_to_migrate, tables_to_migrate = export_storage_metadata(source_project_host, source_api_token)
                migrate_buckets(destination_project_host, destination_api_token, buckets_to_migrate)
                migrate_tables_native_types(destination_project_host, destination_api_token, tables_to_migrate)
                st.write("Migration completed.")
    else:
        st.markdown("Enter hostnames and tokens for both source and destination projects to proceed...")

if __name__ == "__main__":
    main()
