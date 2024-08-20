# Keboola Project Migration
The app migrates Keboola project's metadata (Component - Extractors, Writers, Apps, Transformations, Variables, Shared codes and others configurations) from source to a destination project.
This app doesn't migrate the data, only the configurations. 

# Configuration files
In the app folder, you need to add two configuration JSON files (config_destination.json, config_source.json) to load tokens for the source and target projects (for security reasons, these files are not pushed to GIT).

Example JSON:
```bash
{
  "projects": [
    {
      "name": "TEST 2",
      "url": "https://connection.keboola.com/",
      "token": "TOKEN"
    },
    {
      "name": "TEST 3",
      "url": "https://connection.keboola.com/",
      "token": "TOKEN"
    },
    {
      "name": "TEST 1",
      "url": "https://connection.keboola.com/",
      "token": "TOKEN"
    }
  ]
}

```

## Run app
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


