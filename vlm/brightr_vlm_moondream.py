#!/usr/bin/env python3
"""
Brightr LLM - Moondream2 VLM Deployment
Corrosion Inspection System (Lightweight Version)
Optimized for CPU inference on low-resource systems (Intel Graphics, 15.5GB RAM)
"""

import torch
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer
from pydantic import BaseModel, Field
from typing import Literal

# ============================================================================
# PYDANTIC MODELS FOR VALIDATION
# ============================================================================

class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1, description="Top-left x coordinate (0-1)")
    y: float = Field(ge=0, le=1, description="Top-left y coordinate (0-1)")
    width: float = Field(ge=0, le=1, description="Box width (0-1)")
    height: float = Field(ge=0, le=1, description="Box height (0-1)")

class Detection(BaseModel):
    label: str = Field(..., description="Corrosion type label")
    confidence: float = Field(ge=0, le=1, description="Detection confidence")
    box: BoundingBox

class InspectionResult(BaseModel):
    findingsText: str = Field(..., min_length=10)
    recommendationText: str = Field(..., min_length=10)
    rustGrade: Literal["Ri1", "Ri2", "R3", "R4", "R5"]
    cof: int = Field(..., ge=1, le=5)
    findingsPriority: Literal["low", "medium", "high"]
    sapPriority: Literal["low", "medium", "high"]
    equipmentType: Literal["piping", "pressure_vessel", "flange", "structural", "other"]
    equipmentId: str
    recommendationCode: Literal["TBR", "TBRy", "TBP", "TBM", "TBS"]
    furtherInspection: bool
    openInsulation: bool
    scaffold: bool
    aiConfidence: float = Field(ge=0, le=1)
    detections: List[Detection] = Field(default_factory=list)

# ============================================================================
# SYSTEM PROMPTS (Adapted for Moondream2's conversational style)
# ============================================================================

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TAXONOMY_PATH = _REPO_ROOT / "recommendation_taxonomy.txt"

_SYSTEM_PROMPT_FALLBACK_CONTEXT = """Recommendation codes:
- TBR: To Be Repaired (immediate action required)
- TBRy: To Be Repaired within year (plan within 12 months)
- TBP: To Be Painted (surface treatment needed)
- TBM: To Be Monitored (track condition over time)
- TBS: To Be Scraped (remove loose material/scale)

Rust grade scale (Ri1=minimal, R5=severe):
- Ri1: Surface rust, no pitting, cosmetic only
- Ri2: Light surface corrosion, minor pitting
- R3: Moderate corrosion with visible pitting, some metal loss
- R4: Heavy corrosion, significant metal loss, structural concern
- R5: Severe corrosion, critical metal loss, imminent failure risk

CoF (Consequence of Failure): 1=negligible, 5=catastrophic"""


def _load_taxonomy_text() -> str:
    try:
        if _TAXONOMY_PATH.is_file():
            text = _TAXONOMY_PATH.read_text(encoding="utf-8").strip()
            if text:
                return text
    except OSError:
        pass
    return _SYSTEM_PROMPT_FALLBACK_CONTEXT


def _build_system_prompt() -> str:
    taxonomy = _load_taxonomy_text()
    return f"""You are an expert oil & gas inspection engineer specializing in corrosion assessment. Analyze the provided inspection image and provide a structured assessment.

CONTEXT (recommendation taxonomy and field rules):
{taxonomy}

ANALYSIS REQUIREMENTS:
1. Identify corrosion type, location, extent, and severity
2. Assess structural implications based on visible damage
3. Provide specific, actionable recommendations with timing
4. Estimate rust grade from visual indicators
5. If uncertain, state "Unable to determine from image"

CRITICAL: Respond ONLY with valid JSON. No markdown, no code fences, no extra text.

Use this EXACT schema:
{{
  "findingsText": "Detailed description of corrosion observed",
  "recommendationText": "Specific recommendation with code and timing",
  "rustGrade": "R3",
  "cof": 3,
  "findingsPriority": "medium",
  "sapPriority": "high",
  "equipmentType": "piping",
  "equipmentId": "EQ-SIM-001",
  "recommendationCode": "TBR",
  "furtherInspection": false,
  "openInsulation": false,
  "scaffold": false,
  "aiConfidence": 0.85,
  "detections": [
    {{
      "label": "External corrosion",
      "confidence": 0.87,
      "box": {{"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.25}}
    }}
  ]
}}

Be precise, practical, and conservative. When uncertain, indicate lower confidence and recommend further inspection."""


SYSTEM_PROMPT = _build_system_prompt()

FEW_SHOT_EXAMPLES = """

EXAMPLE 1 - Light Surface Rust:
{
  "findingsText": "Light surface rust observed on carbon steel piping covering approximately 15% of external surface. Orange-brown discoloration typical of early-stage oxidation. No visible pitting or metal loss detected. Protective coating has degraded.",
  "recommendationText": "TBP P3: Clean surface rust and apply protective coating within 90 days. Rust grade Ri2 indicates surface treatment is sufficient at this stage.",
  "rustGrade": "Ri2",
  "cof": 2,
  "findingsPriority": "low",
  "sapPriority": "medium",
  "equipmentType": "piping",
  "equipmentId": "EQ-SIM-001",
  "recommendationCode": "TBP",
  "furtherInspection": false,
  "openInsulation": false,
  "scaffold": false,
  "aiConfidence": 0.92,
  "detections": [
    {"label": "Surface rust", "confidence": 0.95, "box": {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.3}}
  ]
}

EXAMPLE 2 - Severe Pitting:
{
  "findingsText": "Severe pitting corrosion on flange sealing surface with deep cavities (2-4mm estimated depth) affecting 30-40% of sealing area. Heavy rust scale and metal loss present. Flange integrity compromised, leak risk elevated.",
  "recommendationText": "TBR P1: Replace flange immediately due to R4 corrosion severity and critical sealing surface degradation. Potential leak path identified.",
  "rustGrade": "R4",
  "cof": 4,
  "findingsPriority": "high",
  "sapPriority": "high",
  "equipmentType": "flange",
  "equipmentId": "EQ-SIM-002",
  "recommendationCode": "TBR",
  "furtherInspection": true,
  "openInsulation": false,
  "scaffold": true,
  "aiConfidence": 0.88,
  "detections": [
    {"label": "Pitting corrosion", "confidence": 0.91, "box": {"x": 0.15, "y": 0.25, "width": 0.6, "height": 0.5}}
  ]
}

Now analyze the provided image following the same format. Return ONLY the JSON object."""

# ============================================================================
# MOONDREAM2 CORROSION INSPECTION MODEL
# ============================================================================

class CorrosionInspectionModel:
    def __init__(
        self, 
        model_id: str = "vikhyatk/moondream2",
        revision: str = "2024-08-26"
    ):
        """
        Initialize Moondream2 for corrosion inspection.
        
        Args:
            model_id: HuggingFace model identifier
            revision: Model revision/tag
        """
        print("="*80)
        print("BRIGHTR LLM - CORROSION INSPECTION SYSTEM")
        print("Model: Moondream2 (Lightweight VLM)")
        print("="*80)
        
        print(f"\n🔧 Loading model: {model_id}")
        print("⏳ This may take a few minutes on first run (downloading ~3GB)...")
        
        # Load model on CPU with low memory mode
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True,
            torch_dtype=torch.float32,  # FP32 for CPU
            device_map="cpu",
            low_cpu_mem_usage=True
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True
        )
        
        print("✅ Model loaded successfully!\n")
    
    def extract_json_from_response(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from model response, handling extra text.
        
        Args:
            text: Raw model output
            
        Returns:
            Parsed JSON dict or None
        """
        # Remove markdown code fences
        text = re.sub(r'```json\s*|\s*```', '', text)
        text = text.strip()
        
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error: {e}")
                return None
        
        print(f"⚠️  No JSON object found in response")
        return None
    
    def validate_output(self, result: Dict) -> tuple:
        """
        Validate output against Pydantic schema.
        
        Returns:
            Tuple of (is_valid, validated_result, error_message)
        """
        try:
            validated = InspectionResult(**result)
            return True, validated, None
        except Exception as e:
            return False, None, str(e)
    
    def _result_to_dict(self, validated: InspectionResult) -> Dict:
        if hasattr(validated, "model_dump"):
            return validated.model_dump()
        return validated.dict()

    def inference_from_pil(
        self,
        image: Image.Image,
        equipment_id: str = "EQ-SIM-001",
        include_few_shot: bool = True,
        verbose: bool = False,
    ) -> Dict:
        """
        Run corrosion inspection on a PIL image (no filesystem path required).

        Returns:
            Dict with 'success', 'result', 'raw_output', 'error' keys
        """
        if verbose:
            print(f"📋 Equipment ID: {equipment_id}")

        rgb = image.convert("RGB")
        enc_image = self.model.encode_image(rgb)

        prompt = f"Equipment ID: {equipment_id}\n\n"
        prompt += SYSTEM_PROMPT

        if include_few_shot:
            prompt += "\n\n" + FEW_SHOT_EXAMPLES

        prompt += (
            f"\n\nAnalyze this corrosion image for equipment {equipment_id}. "
            "Return ONLY the JSON object with no additional text."
        )

        if verbose:
            print("⚙️  Generating analysis (10-30 seconds on CPU)...")

        answer = self.model.answer_question(enc_image, prompt, self.tokenizer)

        if verbose:
            print("✓ Generation complete")

        parsed = self.extract_json_from_response(answer)

        if parsed is None:
            return {
                "success": False,
                "error": "Failed to parse JSON from model output",
                "result": None,
                "raw_output": answer,
            }

        is_valid, validated, error = self.validate_output(parsed)

        if not is_valid:
            return {
                "success": False,
                "error": f"Validation failed: {error}",
                "result": parsed,
                "raw_output": answer,
            }

        return {
            "success": True,
            "result": self._result_to_dict(validated),
            "raw_output": answer,
            "error": None,
        }

    def inference(
        self,
        image_path: Union[str, Path],
        equipment_id: str = "EQ-SIM-001",
        include_few_shot: bool = True,
        verbose: bool = True,
    ) -> Dict:
        """
        Run corrosion inspection on an image file.

        Returns:
            Dict with 'success', 'result', 'raw_output', 'error' keys
        """
        image_path = Path(image_path)
        if not image_path.exists():
            return {
                "success": False,
                "error": f"Image not found: {image_path}",
                "result": None,
                "raw_output": None,
            }

        if verbose:
            print(f"🔍 Analyzing: {image_path.name}")
            print(f"📋 Equipment ID: {equipment_id}")

        image = Image.open(image_path).convert("RGB")
        return self.inference_from_pil(
            image,
            equipment_id=equipment_id,
            include_few_shot=include_few_shot,
            verbose=verbose,
        )
    
    def batch_inference(
        self, 
        image_paths: List[Union[str, Path]],
        equipment_ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Run inference on multiple images.
        """
        if equipment_ids is None:
            equipment_ids = [f"EQ-SIM-{i:03d}" for i in range(len(image_paths))]
        
        results = []
        total = len(image_paths)
        
        for i, (image_path, eq_id) in enumerate(zip(image_paths, equipment_ids), 1):
            print(f"\n[{i}/{total}] Processing {Path(image_path).name}")
            result = self.inference(image_path, equipment_id=eq_id, **kwargs)
            results.append(result)
        
        return results

# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Brightr LLM Corrosion Inspection System (Moondream2)"
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to corrosion image"
    )
    parser.add_argument(
        "--equipment-id",
        default="EQ-SIM-001",
        help="Equipment identifier (default: EQ-SIM-001)"
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Disable few-shot examples"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="Process multiple images"
    )
    parser.add_argument(
        "--output",
        help="Save results to JSON file"
    )
    
    args = parser.parse_args()
    
    # Initialize model
    model = CorrosionInspectionModel()
    
    # Single image mode
    if args.image:
        result = model.inference(
            image_path=args.image,
            equipment_id=args.equipment_id,
            include_few_shot=not args.no_few_shot
        )
        
        print("\n" + "="*80)
        print("INSPECTION RESULTS")
        print("="*80 + "\n")
        
        if result["success"]:
            print("✅ SUCCESS\n")
            print(json.dumps(result["result"], indent=2))
            
            # Summary
            r = result["result"]
            print(f"\n📊 SUMMARY:")
            print(f"  • Rust Grade: {r['rustGrade']}")
            print(f"  • Recommendation: {r['recommendationCode']}")
            print(f"  • Priority: {r['findingsPriority']}")
            print(f"  • Confidence: {r['aiConfidence']:.1%}")
            print(f"  • Detections: {len(r['detections'])}")
            
        else:
            print(f"❌ FAILED: {result['error']}\n")
            if result.get("raw_output"):
                print("Raw output (first 500 chars):")
                print(result["raw_output"][:500])
        
        # Save if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
    
    # Batch mode
    elif args.batch:
        results = model.batch_inference(args.batch)
        
        print("\n" + "="*80)
        print(f"BATCH RESULTS ({len(results)} images)")
        print("="*80 + "\n")
        
        for i, res in enumerate(results, 1):
            status = "✅" if res["success"] else "❌"
            print(f"{i}. {status} {Path(args.batch[i-1]).name}")
            if res["success"]:
                print(f"   Grade: {res['result']['rustGrade']}, "
                      f"Rec: {res['result']['recommendationCode']}, "
                      f"Conf: {res['result']['aiConfidence']:.1%}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
    
    # Interactive mode
    else:
        print("\n" + "="*80)
        print("INTERACTIVE MODE")
        print("="*80)
        print("\nUsage:")
        print("  python brightr_vlm_moondream.py <image_path>")
        print("  python brightr_vlm_moondream.py --batch img1.jpg img2.jpg img3.jpg")
        print("\nOptions:")
        print("  --equipment-id EQ-001    Set equipment ID")
        print("  --no-few-shot           Disable examples")
        print("  --output results.json   Save results to file")
        print("\nExample:")
        print("  python brightr_vlm_moondream.py valve-corrosion.jpg --equipment-id VALVE-001")

if __name__ == "__main__":
    main()
