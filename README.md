# Keboola Project Migration
The app migrates Keboola project's metadata (Component - Extractors, Writers, Apps, Transformations, Variables, Shared codes and others configurations as well as Storage object definitions) from source to a destination project.
This app doesn't migrate the data, only the configurations. 


To execute the app it's recommended to fetch the repository to local machine and run it in virtual environment. Clone it, navigate to the cloned folder and execute the following.

1. Create a virtual environment named 'venv'
```bash
python -m venv venv
```

2. Activate the virtual environment
```bash
.\venv\Scripts\activate
```

3. Upgrade pip (optional but recommended)
```bash
python -m pip install --upgrade pip
```

4. Install the required packages from requirements.txt
```bash
pip install -r requirements.txt
```

5. Run the app
```bash
streamlit run app/migrate.py
```



## Configration Migration
Migrates all components including all Extractors, Writers, Apps, Flows, Variables, Shared codes, Transformations. It allows user to select specific components that should be migrated or skipped.

## Storage Migration
Migrates all storage buckets and tables (only definitions). It doesn't migrate data, only creates empty tables in the destination project. It supports Native Types if needed. 
