from flask import Flask, render_template, request
import pandas as pd
import requests
import io

app = Flask(__name__)

# Function to download the dataset from Google Drive
def download_dataset():
    file_id = '1NANSg7fXFiWTRtS1GJJy5zUtK-R6hbg6'
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to download file, status code: {response.status_code}")

# Function to load the CSV data into a DataFrame
def load_raw_data(csv_data):
    try:
        df = pd.read_csv(io.StringIO(csv_data), delimiter=';', engine='python')
        return df
    except Exception as e:
        raise Exception(f"Error loading CSV into DataFrame: {e}")

# Function to clean the data
def clean_data(df):
    df = df.dropna(how='all')
    df = df.ffill()

    if 'Quoting Price' in df.columns:
        df['Quoting Price'] = df['Quoting Price'].str.replace(',', '.').astype(float)

    return df

# Function to filter data based on price range
def filter_by_price_range(df, target_price, gap=0.5):
    range_start = target_price - (target_price % gap)
    range_end = range_start + gap
    range_start = max(range_start, 0.5)
    range_end = min(range_end, 6)
    
    return df[(df['Quoting Price'] >= range_start) & (df['Quoting Price'] < range_end)]

# Route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    budget = None
    projects = []
    data = []

    if request.method == 'POST':
        try:
            budget = float(request.form.get('budget'))
            csv_data = download_dataset()
            df_raw = load_raw_data(csv_data)
            df_cleaned = clean_data(df_raw)
            
            # Filter the data based on the budget
            df_filtered = filter_by_price_range(df_cleaned, budget)
            projects = df_filtered['Project Name'].unique()
            data = df_filtered.to_dict(orient='records')
        
        except Exception as e:
            print(f"Error: {e}")
    
    return render_template('index.html', budget=budget, data=data, projects=projects)

# Route to filter projects based on selected project name
@app.route('/filter_projects', methods=['POST'])
def filter_projects():
    budget = float(request.form.get('budget'))
    project_name = request.form.get('project_name')
    
    try:
        csv_data = download_dataset()
        df_raw = load_raw_data(csv_data)
        df_cleaned = clean_data(df_raw)
        df_filtered = filter_by_price_range(df_cleaned, budget)
        df_project_filtered = df_filtered[df_filtered['Project Name'] == project_name]
        
        carpet_sizes = df_project_filtered[['Carpet Size']].drop_duplicates().reset_index(drop=True)
        carpet_sizes = carpet_sizes.to_dict(orient='records')
        
    except Exception as e:
        print(f"Error: {e}")
        carpet_sizes = []

    return render_template('results.html', budget=budget, carpet_sizes=carpet_sizes, data=df_project_filtered.to_dict(orient='records'), project_name=project_name)

# Route to display details of a selected carpet size
@app.route('/details', methods=['POST'])
def details():
    carpet_size = request.form.get('carpet_size')
    budget = float(request.form.get('budget'))
    project_name = request.form.get('project_name')
    
    try:
        # Download and process the CSV
        csv_data = download_dataset()
        df_raw = load_raw_data(csv_data)
        df_cleaned = clean_data(df_raw)

        # Filter the data
        df_filtered = filter_by_price_range(df_cleaned, budget)
        df_project_filtered = df_filtered[df_filtered['Project Name'] == project_name]

        # Check if we have valid rows for the selected carpet size
        selected_row = df_project_filtered[df_project_filtered['Carpet Size'].astype(str).str.contains(carpet_size, na=False)]

        if not selected_row.empty:
            layout_url = selected_row['Layout'].values[0]
            image_url = layout_url  # Use the direct image URL
            
            details = {
                'project_name': selected_row['Project Name'].values[0],
                'configuration': selected_row['Configuration'].values[0],
                'carpet_size': selected_row['Carpet Size'].values[0],
                'quoting_price': selected_row['Quoting Price'].values[0],
                'layout_url': layout_url,
                'image_url': image_url
            }

            return render_template('details.html', details=details)
        else:
            return "No details found for the selected carpet size."
    
    except Exception as e:
        print(f"Error: {e}")
        return f"Error occurred while fetching details: {e}"

if __name__ == '__main__':
    app.run(debug=True, port=5001)
