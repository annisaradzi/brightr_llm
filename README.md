# Photo Analysis Pipeline

A Streamlit-based application that analyzes images using Google Gemini Vision API, extracts structured findings and recommendations, and generates downloadable PDF reports.

## Features

- 📸 **Image Upload**: Support for PNG, JPG, JPEG, and WEBP formats (up to 10MB)
- 🤖 **AI-Powered Analysis**: Uses Google Gemini Vision API for intelligent image analysis
- 📊 **Structured Output**: Extracts findings and recommendations in a structured JSON format
- 📋 **Tabulated Results**: Displays findings and recommendations in easy-to-read tables
- 📄 **PDF Report Generation**: Automatically generates professional PDF reports with formatted tables
- 💾 **Download Reports**: One-click download of generated PDF reports

## Prerequisites

- Python 3.10 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API key**:
   - Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env  # Windows
     cp .env.example .env    # macOS/Linux
     ```
   - Edit `.env` and set your Gemini API key:
     ```
     GEMINI_API_KEY=your-actual-api-key-here
     ```

## Usage

1. **Start the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`)

3. **Upload an image**:
   - Click "Browse files" or drag and drop an image
   - Supported formats: PNG, JPG, JPEG, WEBP
   - Maximum file size: 10MB

4. **Analyze the image**:
   - Click the "Analyze image" button
   - Wait for the AI analysis to complete

5. **Review results**:
   - View the executive summary
   - Browse findings in the table
   - Review recommendations in the table

6. **Download PDF report**:
   - Click "Download PDF report" button
   - The report includes all analysis data in a formatted PDF

## Customizing the System Prompt

The application uses a system prompt to guide the AI analysis. You can customize it:

1. **Edit `system_prompt` file**:
   - Modify the prompt to change the analysis focus or output format
   - The prompt should request JSON output with `summary`, `findings`, and `recommendations` fields

2. **Default prompt**:
   - If `system_prompt` file doesn't exist, the app uses a built-in default prompt
   - The default is optimized for oil & gas corrosion inspection

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `GEMINI_MODEL`: Model to use (default: `gemini-1.5-pro`)

### File Limits

- Maximum upload size: 10MB (configurable in `app.py`: `MAX_UPLOAD_MB`)
- Supported formats: PNG, JPG, JPEG, WEBP (configurable in `app.py`: `SUPPORTED_EXTS`)

## Project Structure

```
brightr_llm/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── .env                  # Your API key (create this, not in git)
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── system_prompt       # Customizable AI prompt (optional)
└── reports/            # Generated PDF reports (created at runtime)
```

## How It Works

1. **Image Upload**: User uploads an image through Streamlit's file uploader
2. **Image Processing**: Image is validated and converted to RGB format
3. **AI Analysis**: 
   - System prompt is loaded from `system_prompt` file (or uses default)
   - Image and prompt are sent to Google Gemini Vision API
   - Response is parsed to extract structured JSON data
4. **Results Display**: 
   - Summary, findings, and recommendations are displayed in the UI
   - Data is shown in tables for easy reading
5. **PDF Generation**: 
   - ReportLab generates a formatted PDF with all analysis data
   - PDF is saved to `reports/` directory and made available for download

## Dependencies

- `streamlit`: Web application framework
- `google-generativeai`: Google Gemini API client
- `reportlab`: PDF generation library
- `python-dotenv`: Environment variable management
- `Pillow`: Image processing
- `pandas`: Data manipulation for tables

## Troubleshooting

### "Missing GEMINI_API_KEY" warning
- Ensure you've created a `.env` file from `.env.example`
- Verify your API key is correctly set in `.env`
- Restart the Streamlit app after creating/editing `.env`

### "Gemini analysis failed" error
- Check your API key is valid and has sufficient quota
- Verify you have internet connectivity
- Check the model name in `GEMINI_MODEL` environment variable

### PDF generation fails
- Ensure write permissions for the `reports/` directory
- Check available disk space

### Image upload issues
- Verify file format is supported (PNG, JPG, JPEG, WEBP)
- Check file size is under 10MB
- Ensure the image file is not corrupted

## License

This project is provided as-is for educational and development purposes.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the error messages in the Streamlit UI
3. Check the "Raw model output (debug)" expander if analysis fails
