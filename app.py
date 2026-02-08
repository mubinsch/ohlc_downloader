from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import sys

# Add parent directory to path to import your modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.get_and_clean_data import get_and_clean_data
from utils.plot_candlestick import plot_candlestick
from utils.normalize_data import normalize_symbol

app = Flask(__name__)
CORS(app)

# Ensure directories exist
os.makedirs('temp', exist_ok=True)
os.makedirs('downloads', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download-csv', methods=['POST'])
def download_csv():
    try:
        data = request.json
        
        # Parse parameters
        symbols = data.get('asset', '').strip().split()
        tf = int(data.get('tf', 15))
        date_mode = data.get('date_mode', 'lookback')
        timezone = data.get('timezone', 'utc+3:30')
        
        # Handle date mode
        if date_mode == 'lookback':
            output_candles = int(data.get('output_candles', 85))
            from_date_str = None
            to_date_str = None
            date_range = False
        else:
            from_date_str = data.get('from_date')
            to_date_str = data.get('to_date')
            output_candles = None
            date_range = True
        
        # Process each symbol
        all_dfs = {}
        for symbol in symbols:
            try:
                df = get_and_clean_data(
                    date_range=date_range,
                    from_date_str=from_date_str,
                    to_date_str=to_date_str,
                    ohlc_tz_str=timezone,
                    output_candles=output_candles,
                    tf=tf,
                    asset=symbol
                )
                
                if df is not None and not df.empty:
                    all_dfs[symbol] = df
                    print(f"✓ Successfully fetched {len(df)} candles for {symbol}")
                else:
                    print(f"✗ No data returned for {symbol}")
            except Exception as e:
                print(f"✗ Error fetching {symbol}: {e}")
                continue
        
        if not all_dfs:
            return jsonify({'error': 'No data could be fetched for any symbol'}), 400
        
        # If single symbol, return CSV directly
        if len(all_dfs) == 1:
            symbol = list(all_dfs.keys())[0]
            df = all_dfs[symbol]
            
            # Convert to CSV
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=True)
            csv_buffer.seek(0)
            
            filename = f"{symbol}_{tf}m_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return send_file(
                csv_buffer,
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        else:
            # Multiple symbols - create ZIP with multiple CSVs
            import zipfile
            
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for symbol, df in all_dfs.items():
                    csv_str = df.to_csv(index=True)
                    csv_bytes = csv_str.encode('utf-8')
                    filename = f"{symbol}_{tf}m_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    zip_file.writestr(filename, csv_bytes)
            
            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"ohlc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
            
    except Exception as e:
        print(f"Error in download_csv: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.json
        
        # Parse parameters
        data_source = data.get('data_source', 'fetch')
        symbols = data.get('symbols', '').strip().split()
        tf = int(data.get('tf', 15))
        timezone = data.get('timezone', 'utc+3:30')
        chart_width = float(data.get('chart_width', 16))
        chart_height_per_symbol = float(data.get('chart_height', 6))
        candle_width = float(data.get('candle_width', 0.6))
        
        # Handle date mode
        date_mode = data.get('date_mode', 'lookback')
        if date_mode == 'lookback':
            output_candles = int(data.get('output_candles', 85))
            from_date_str = None
            to_date_str = None
            date_range = False
        else:
            from_date_str = data.get('from_date')
            to_date_str = data.get('to_date')
            output_candles = None
            date_range = True
        
        # Fetch or load data
        all_dfs = {}
        
        if data_source == 'fetch':
            # Fetch data for each symbol
            for symbol in symbols:
                try:
                    df = get_and_clean_data(
                        date_range=date_range,
                        from_date_str=from_date_str,
                        to_date_str=to_date_str,
                        ohlc_tz_str=timezone,
                        output_candles=output_candles,
                        tf=tf,
                        asset=symbol
                    )
                    
                    if df is not None and not df.empty:
                        all_dfs[symbol] = df
                        print(f"✓ Fetched {len(df)} candles for {symbol}")
                    else:
                        print(f"✗ No data for {symbol}")
                except Exception as e:
                    print(f"✗ Error fetching {symbol}: {e}")
                    continue
        else:
            # This would handle uploaded CSV files
            # For now, we'll skip this since it requires file upload handling
            return jsonify({'error': 'CSV upload not yet implemented in this endpoint'}), 400
        
        if not all_dfs:
            return jsonify({'error': 'No data available to plot'}), 400
        
        # Create figure with subplots
        num_symbols = len(all_dfs)
        fig_height = chart_height_per_symbol * num_symbols
        
        fig, axes = plt.subplots(
            num_symbols, 1,
            figsize=(chart_width, fig_height),
            facecolor='#131722',
            squeeze=False
        )
        
        # Plot each symbol
        for idx, (symbol, df) in enumerate(all_dfs.items()):
            ax = axes[idx, 0]
            
            plot_candlestick(
                ax=ax,
                df=df,
                tf=tf,
                ticker=symbol,
                timezone=timezone,
                up_color='#fbc02d',
                down_color='#9598a1',
                edge_color=None,
                wick_color=None,
                volume_color='#7cb5ec',
                bg_color='#131722',
                grid_color='#e0e0e0',
                grid_style='--',
                grid_alpha=0.3,
                show_grid=False,
                candle_width=candle_width,
                date_format='%m/%d %H:%M',
                rotation=45,
                show_nontrading=False,
                title_fontsize=14,
                title_fontweight='bold',
                title_color='white',
                label_fontsize=11,
                label_color='#d1d4dc',
                tick_fontsize=9,
                tick_color='#787b86',
                spine_color='#2a2e39',
                spine_linewidth=1,
                show_top_spine=False,
                show_right_spine=False,
                y_padding=0.05
            )
            
            # Add right margin for price line
            xlim = ax.get_xlim()
            ax.set_xlim(xlim[0], xlim[1] + 8)
        
        plt.tight_layout()
        
        # Save to PDF buffer
        pdf_buffer = BytesIO()
        fig.savefig(pdf_buffer, format='pdf', bbox_inches='tight', dpi=150)
        plt.close(fig)
        
        pdf_buffer.seek(0)
        
        filename = f"candlestick_{'_'.join(symbols)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error in generate_pdf: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        all_dfs = {}
        
        for file in files:
            if file.filename.endswith('.csv'):
                try:
                    # Read CSV
                    df = pd.read_csv(file, index_col=0, parse_dates=True)
                    
                    # Extract symbol from filename (simple heuristic)
                    symbol = file.filename.replace('.csv', '').split('_')[0]
                    
                    all_dfs[symbol] = df
                    print(f"✓ Loaded {len(df)} candles from {file.filename}")
                except Exception as e:
                    print(f"✗ Error loading {file.filename}: {e}")
                    continue
        
        if not all_dfs:
            return jsonify({'error': 'No valid CSV files loaded'}), 400
        
        # Store in temp directory for later use
        temp_key = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_path = os.path.join('temp', f"{temp_key}.pkl")
        
        import pickle
        with open(temp_path, 'wb') as f:
            pickle.dump(all_dfs, f)
        
        return jsonify({
            'success': True,
            'temp_key': temp_key,
            'symbols': list(all_dfs.keys()),
            'message': f'Successfully loaded {len(all_dfs)} CSV files'
        })
        
    except Exception as e:
        print(f"Error in upload_csv: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)