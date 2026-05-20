#!/usr/bin/env python3
"""
Quick test script for Brightr LLM Corrosion Inspection System
Tests model loading and basic inference
"""

from brightr_vlm_moondream import CorrosionInspectionModel
import json

def test_model_loading():
    """Test 1: Model loads successfully"""
    print("TEST 1: Loading Moondream2 model...")
    try:
        model = CorrosionInspectionModel()
        print("✅ PASS: Model loaded successfully\n")
        return model
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return None

def test_inference(model, image_path):
    """Test 2: Inference runs and returns valid JSON"""
    print(f"TEST 2: Running inference on {image_path}...")
    
    try:
        result = model.inference(
            image_path=image_path,
            equipment_id="TEST-001",
            verbose=False
        )
        
        if result["success"]:
            print("✅ PASS: Inference successful")
            print(f"   Rust Grade: {result['result']['rustGrade']}")
            print(f"   Recommendation: {result['result']['recommendationCode']}")
            print(f"   Confidence: {result['result']['aiConfidence']:.2%}\n")
            return True
        else:
            print(f"❌ FAIL: {result['error']}\n")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False

def test_validation():
    """Test 3: Pydantic validation catches errors"""
    print("TEST 3: Testing validation...")
    
    # Invalid data (bad rust grade)
    from brightr_vlm_moondream import InspectionResult
    
    try:
        invalid_data = {
            "findingsText": "Test findings",
            "recommendationText": "Test recommendation",
            "rustGrade": "INVALID",  # Should fail
            "cof": 3,
            "findingsPriority": "medium",
            "sapPriority": "high",
            "equipmentType": "piping",
            "equipmentId": "TEST-001",
            "recommendationCode": "TBR",
            "furtherInspection": False,
            "openInsulation": False,
            "scaffold": False,
            "aiConfidence": 0.85,
            "detections": []
        }
        
        result = InspectionResult(**invalid_data)
        print("❌ FAIL: Validation should have caught invalid rust grade\n")
        return False
        
    except Exception as e:
        print(f"✅ PASS: Validation correctly caught error: {type(e).__name__}\n")
        return True

def main():
    print("="*80)
    print("BRIGHTR LLM - CORROSION INSPECTION SYSTEM TEST SUITE")
    print("="*80 + "\n")
    
    # Test 1: Model loading
    model = test_model_loading()
    if model is None:
        print("❌ CRITICAL: Cannot proceed without model\n")
        return
    
    # Test 2: Inference (requires test image)
    import sys
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        test_inference(model, test_image)
    else:
        print("TEST 2: SKIPPED (no test image provided)")
        print("   Usage: python test_brightr.py path/to/test-image.jpg\n")
    
    # Test 3: Validation
    test_validation()
    
    print("="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
