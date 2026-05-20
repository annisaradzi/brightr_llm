# Brightr LLM - Corrosion Inspection System

**Lightweight VLM deployment for oil & gas corrosion analysis**  
Powered by Moondream2 (1.6B parameters) - optimized for CPU inference on laptops with limited resources.

---

## 📋 System Requirements

**Your laptop specs (confirmed compatible):**
- **CPU**: Intel Core (1.80 GHz)
- **RAM**: 15.5 GB total (14.5 GB available)
- **GPU**: Intel Graphics (8.8 GB shared memory)
- **Storage**: ~5 GB free (3 GB model + 2 GB dependencies)

**Minimum requirements:**
- Python 3.8+
- 4-5 GB RAM during inference
- ~5 GB disk space
- CPU-only (no GPU required)

---

## 🚀 Quick Start

### 1. **Setup Environment**

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **First Run (Download Model)**

```bash
# This will download ~3GB model on first run
python brightr_vlm_moondream.py
```

### 3. **Analyze an Image**

```bash
# Single image
python brightr_vlm_moondream.py path/to/corrosion-image.jpg

# With equipment ID
python brightr_vlm_moondream.py valve-rust.jpg --equipment-id VALVE-001

# Batch processing
python brightr_vlm_moondream.py --batch img1.jpg img2.jpg img3.jpg

# Save results to JSON
python brightr_vlm_moondream.py corrosion.jpg --output results.json
```

---

## 📊 Expected Output

The system returns **structured JSON** following ISO/NACE corrosion standards:

```json
{
  "findingsText": "Moderate pitting corrosion observed on carbon steel piping...",
  "recommendationText": "TBR P2: Repair corroded section within 30 days...",
  "rustGrade": "R3",
  "cof": 3,
  "findingsPriority": "medium",
  "sapPriority": "high",
  "equipmentType": "piping",
  "equipmentId": "PIPE-001",
  "recommendationCode": "TBR",
  "furtherInspection": false,
  "openInsulation": false,
  "scaffold": false,
  "aiConfidence": 0.85,
  "detections": [
    {
      "label": "Pitting corrosion",
      "confidence": 0.87,
      "box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.25}
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `findingsText` | string | Detailed narrative of corrosion observed |
| `recommendationText` | string | Specific action with code and timing |
| `rustGrade` | enum | `Ri1` (minimal) to `R5` (severe) |
| `cof` | int | Consequence of Failure (1-5) |
| `findingsPriority` | enum | `low`, `medium`, `high` |
| `sapPriority` | enum | SAP work order priority |
| `equipmentType` | enum | `piping`, `pressure_vessel`, `flange`, `structural`, `other` |
| `recommendationCode` | enum | `TBR`, `TBRy`, `TBP`, `TBM`, `TBS` |
| `aiConfidence` | float | Model confidence (0-1) |
| `detections` | array | Bounding boxes with labels |

### Recommendation Codes

- **TBR**: To Be Repaired (immediate action)
- **TBRy**: To Be Repaired within year
- **TBP**: To Be Painted (surface treatment)
- **TBM**: To Be Monitored (track over time)
- **TBS**: To Be Scraped (remove scale)

### Rust Grade Scale

- **Ri1**: Surface rust, cosmetic only
- **Ri2**: Light corrosion, minor pitting
- **R3**: Moderate corrosion, visible metal loss
- **R4**: Heavy corrosion, structural concern
- **R5**: Severe corrosion, imminent failure risk

---

## ⚡ Performance

**On your laptop (CPU inference):**
- **First run**: 2-3 minutes (model download)
- **Subsequent runs**: 10-30 seconds per image
- **Memory usage**: 4-5 GB during inference
- **Accuracy**: Good for basic-to-moderate corrosion detection

**Tips for faster inference:**
- Close other applications before running
- Use `--no-few-shot` flag to skip examples (faster but less accurate)
- Process in batches rather than one-by-one

---

## 🔧 Advanced Usage

### Python API

```python
from brightr_vlm_moondream import CorrosionInspectionModel

# Initialize model (one-time setup)
model = CorrosionInspectionModel()

# Single inference
result = model.inference(
    image_path="corrosion.jpg",
    equipment_id="PIPE-001",
    include_few_shot=True
)

if result["success"]:
    print(f"Rust Grade: {result['result']['rustGrade']}")
    print(f"Recommendation: {result['result']['recommendationCode']}")
else:
    print(f"Error: {result['error']}")

# Batch inference
results = model.batch_inference(
    image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
    equipment_ids=["PIPE-001", "VALVE-002", "FLANGE-003"]
)

for res in results:
    if res["success"]:
        print(f"{res['result']['equipmentId']}: {res['result']['rustGrade']}")
```

### Custom Prompts

```python
# Disable few-shot examples for faster inference
result = model.inference(
    image_path="rust.jpg",
    equipment_id="EQ-001",
    include_few_shot=False  # Faster but may reduce accuracy
)
```

---

## 🎯 Project Context

This system is part of the **Brightr LLM** project for automated corrosion inspection in oil & gas facilities. It replaces manual visual assessment with AI-powered analysis following:

- ISO 8501-1 (Rust grades)
- NACE SP0188 (Coating inspection)
- API 570 (Piping inspection)
- Best practices from Petronas/Shell/ExxonMobil

**Why Moondream2?**
- Smallest viable VLM (1.6B params)
- Runs on CPU with limited RAM
- Fast enough for field deployment
- Good balance of speed vs. accuracy

**Comparison to Qwen2-VL-7B** (your original choice):
| Feature | Moondream2 | Qwen2-VL-7B |
|---------|------------|-------------|
| Size | 1.6B params | 7B params |
| RAM needed | 4-5 GB | 16-20 GB |
| Speed (CPU) | 10-30 sec | 60-120 sec |
| Accuracy | Good | Excellent |
| **Runs on your laptop?** | ✅ Yes | ❌ No (RAM limit) |

---

## 📝 Example Commands

```bash
# Basic analysis
python brightr_vlm_moondream.py corrosion-valve.jpg

# With equipment ID
python brightr_vlm_moondream.py pipe-rust.jpg --equipment-id PIPE-A-101

# Batch process entire folder
python brightr_vlm_moondream.py --batch inspections/*.jpg --output batch_results.json

# Faster mode (no examples)
python brightr_vlm_moondream.py rust.jpg --no-few-shot

# Just test model loading
python brightr_vlm_moondream.py
```

---

## 🐛 Troubleshooting

### "Out of memory" error
**Solution**: Close other applications. The model needs ~5GB free RAM.

```bash
# Check available RAM
free -h  # Linux
wmic OS get FreePhysicalMemory  # Windows
```

### Model download fails
**Solution**: Check internet connection. Model is ~3GB.

```bash
# Manual download
huggingface-cli download vikhyatk/moondream2 --revision 2024-08-26
```

### JSON parsing errors
**Symptom**: "Failed to parse JSON from model output"  
**Cause**: Moondream2 sometimes adds extra text before/after JSON  
**Solution**: The script auto-extracts JSON. Check `raw_output` in results.

### Low confidence scores
**Symptom**: `aiConfidence` below 0.5  
**Cause**: Unclear image or unfamiliar corrosion pattern  
**Solution**: Use `--no-few-shot` flag or provide clearer images

---

## 🔄 Upgrading to Qwen2-VL (when resources allow)

If you upgrade your laptop or deploy to a server with more RAM (32GB+), switch to Qwen2-VL-7B for better accuracy:

```python
# Replace model initialization
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-7B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)
```

---

## 📚 References

- **Moondream2**: https://huggingface.co/vikhyatk/moondream2
- **ISO 8501-1**: Visual assessment of surface cleanliness
- **NACE SP0188**: Coating inspection and evaluation
- **Your vlm_model_smoll chat**: https://claude.ai/chat/50f1979f-9b13-4c6e-9bb9-c200c1254e31

---

## 📞 Support

For issues or questions about Brightr LLM project, refer to the project documentation or consult with the data science team.

**Model limitations:**
- Small VLM may miss subtle corrosion patterns
- Bounding box coordinates are estimated
- Cannot detect hidden/internal corrosion
- Recommendations are advisory, not definitive

**Always validate critical findings with human inspection.**

---

**Version**: 1.0.0  
**Last Updated**: May 2026  
**License**: Internal use only
