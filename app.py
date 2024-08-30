from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import requests
import io

app = Flask(__name__)

def download_dataset():
    file_id = '1NANSg7fXFiWTRtS1GJJy5zUtK-R6hbg6'
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to download file, status code: {response.status_code}")

def load_raw_data(csv_data):
    try:
        df = pd.read_csv(io.StringIO(csv_data), delimiter=';', engine='python')
        return df
    except Exception as e:
        raise Exception(f"Error loading CSV into DataFrame: {e}")

def clean_data(df):
    df = df.dropna(how='all')
    df = df.ffill()
    df['Carpet Size'] = df['Carpet Size'].astype(str).replace(r'\.0$', '', regex=True)
    df['Quoting Price'] = df['Quoting Price'].str.replace(',', '.').astype(float)
    return df

def filter_by_price_range(df, target_price, gap=0.5):
    range_start = target_price - (target_price % gap)
    range_end = range_start + gap
    range_start = max(range_start, 0.5)
    range_end = min(range_end, 6)
    return df[(df['Quoting Price'] >= range_start) & (df['Quoting Price'] < range_end)]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            budget = float(request.form.get('budget'))
        except ValueError:
            return redirect(url_for('index'))  # Redirect if budget conversion fails
        
        csv_data = download_dataset()
        df_raw = load_raw_data(csv_data)
        df_cleaned = clean_data(df_raw)
        df_filtered = filter_by_price_range(df_cleaned, budget)
        
        projects = df_filtered['Project Name'].unique()
        data = df_filtered.to_dict(orient='records')

        return render_template('results.html', budget=budget, data=data, projects=projects)
    
    return render_template('index.html')

@app.route('/details', methods=['POST'])
def details():
    try:
        budget = float(request.form.get('budget'))
        project_name = request.form.get('project_name')
        carpet_size = request.form.get('carpet_size')
    except ValueError:
        return redirect(url_for('index'))  # Redirect if conversion fails

    csv_data = download_dataset()
    df_raw = load_raw_data(csv_data)
    df_cleaned = clean_data(df_raw)
    
    df_filtered = filter_by_price_range(df_cleaned, budget)
    df_project_filtered = df_filtered[df_filtered['Project Name'] == project_name]
    
    selected_row = df_project_filtered[df_project_filtered['Carpet Size'] == carpet_size]
    
    if not selected_row.empty:
        details = {
            'project_name': selected_row['Project Name'].values[0],
            'configuration': selected_row['Configuration'].values[0],
            'carpet_size': selected_row['Carpet Size'].values[0],
            'quoting_price': selected_row['Quoting Price'].values[0],
            'image_url': selected_row['Layout'].values[0]  # Assuming layout URL is used for the image
        }
        
        return render_template('details.html', details=details)

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
