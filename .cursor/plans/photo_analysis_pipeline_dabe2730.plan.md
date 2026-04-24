---
name: Photo Analysis Pipeline
overview: Build a Streamlit-based photo analysis pipeline that uploads images, analyzes them using Google Gemini Vision API, displays findings and recommendations, and generates downloadable PDF reports.
todos:
  - id: setup_files
    content: "Create project setup files: requirements.txt, .gitignore, .env.example, README.md"
    status: completed
  - id: streamlit_app
    content: Create main Streamlit app.py with file uploader, image preview, and UI layout
    status: completed
  - id: gemini_integration
    content: Implement Google Gemini Vision API integration for image analysis
    status: completed
  - id: response_parsing
    content: Create function to parse Gemini response and extract findings, recommendations, and summary
    status: completed
  - id: pdf_generation
    content: Implement PDF report generation using ReportLab with formatted tables
    status: completed
  - id: download_functionality
    content: Add PDF download button and file serving in Streamlit
    status: completed
  - id: error_handling
    content: Add comprehensive error handling for API calls, file operations, and PDF generation
    status: completed
isProject: false
---

# Photo Analysis Pipeline - Implementation Plan

## Architecture Overview

The application will be a single Streamlit app that handles:

- Image upload via Streamlit's file uploader
- Image analysis using Google Gemini Vision API
- Results display with tabulated findings and recommendations
- PDF report generation using ReportLab
- PDF download functionality

## Project Structure

```
brightr_llm/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
├── README.md             # Project documentation
└── reports/              # Generated PDF reports (auto-created)
```

## Implementation Steps

### 1. Project Setup Files

**`requirements.txt`**

- streamlit (UI framework)
- google-generativeai (Gemini API client)
- reportlab (PDF generation)
- python-dotenv (environment variable management)
- Pillow (image processing)

**`.gitignore`**

- Python cache files
- Virtual environments
- Environment files (.env)
- Generated reports directory
- Streamlit cache

**`.env.example`**

- Template with GOOGLE_API_KEY placeholder

**`README.md`**

- Setup instructions
- API key configuration
- Usage guide
- Project structure

### 2. Main Application (`app.py`)

The Streamlit app will have the following components:

**Image Upload Section**

- Use `st.file_uploader` with image type restrictions
- Display image preview after upload
- Validate file size and format

**Analysis Function**

- Encode image to base64 or use PIL Image
- Call Google Gemini Vision API with prompt for structured analysis
- Parse response to extract findings, recommendations, and summary
- Handle API errors gracefully

**Results Display**

- Executive summary section
- Findings table/list (using `st.dataframe` or `st.markdown`)
- Recommendations table/list
- Success/error messages

**PDF Generation**

- Use ReportLab to create formatted PDF
- Include:
  - Title and timestamp
  - Executive summary
  - Findings table
  - Recommendations table
- Save to `reports/` directory with unique filename

**Download Section**

- Display download button when report is ready
- Use `st.download_button` to serve PDF file
- Generate unique report ID for tracking

### 3. Key Functions

**`analyze_image_with_gemini(image, api_key)`**

- Takes PIL Image or file path
- Configures Gemini client
- Sends image with analysis prompt
- Returns structured dict with findings, recommendations, summary
- Handles JSON parsing from Gemini response

**`create_pdf_report(analysis_data, report_path)`**

- Creates PDF using ReportLab
- Formats with proper styling (tables, headings, spacing)
- Includes all analysis data
- Returns file path

**`parse_gemini_response(response_text)`**

- Extracts structured data from Gemini's text response
- Handles both JSON and natural language formats
- Falls back to text parsing if JSON parsing fails

### 4. Streamlit UI Layout

- Header with title and description
- File uploader widget
- Image preview (when uploaded)
- Analyze button (disabled until image uploaded)
- Loading spinner during analysis
- Results sections (summary, findings, recommendations)
- Download button (appears after analysis)

### 5. Error Handling

- Invalid file type validation
- API key missing/incorrect
- API rate limits/errors
- Image processing errors
- PDF generation failures

### 6. Environment Configuration

- Load API key from `.env` file
- Provide clear error if API key missing
- Instructions in UI for setting up API key

## Technical Details

**Google Gemini Integration**

- Use `google.generativeai` library
- Model: `gemini-pro-vision` or `gemini-1.5-pro`
- Prompt engineering to get structured JSON response
- Handle image encoding (base64 or direct PIL Image)

**PDF Report Format**

- A4 page size
- Professional styling with ReportLab
- Table formatting for findings/recommendations
- Header with timestamp
- Footer with report ID

**Streamlit Features**

- Session state for managing uploads and results
- File handling with temporary storage
- Download button for PDF
- Responsive layout

## Dependencies

- streamlit >= 1.28.0
- google-generativeai >= 0.3.0
- reportlab >= 4.0.0
- python-dotenv >= 1.0.0
- Pillow >= 10.0.0

## Testing Considerations

- Test with various image formats (JPG, PNG, WEBP)
- Test with different image sizes
- Test API error scenarios
- Test PDF generation with various data lengths
- Verify download functionality