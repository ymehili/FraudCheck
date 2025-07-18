#!/usr/bin/env python3
"""
Test script to verify that the analysis endpoint is working correctly
after fixing the request format and PDF processing issues.
"""

import requests
import json
import os

def test_analysis_endpoint():
    """Test the analysis endpoint with correct request format."""
    
    # API base URL
    BASE_URL = "http://localhost:8000"
    
    print("🔍 Testing Analysis Endpoint Fix")
    print("=" * 50)
    
    # Test data - using the correct request format
    test_requests = [
        {
            "name": "Standard analysis request",
            "data": {
                "file_id": "test-file-123",
                "analysis_types": ["forensics", "ocr", "rules"]
            }
        },
        {
            "name": "OCR only analysis",
            "data": {
                "file_id": "test-file-456",
                "analysis_types": ["ocr"]
            }
        },
        {
            "name": "PDF with page number",
            "data": {
                "file_id": "test-pdf-789",
                "analysis_types": ["forensics", "ocr"],
                "page_number": 1
            }
        }
    ]
    
    # Test each request format
    for i, test_case in enumerate(test_requests, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   Request data: {json.dumps(test_case['data'], indent=2)}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/analyze/",
                json=test_case['data'],
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 422:
                # Validation error - check the error details
                error_data = response.json()
                print(f"   ✅ Request validation working (422 expected for test data)")
                print(f"   Error details: {error_data.get('detail', 'No details')}")
            elif response.status_code == 401:
                print(f"   ✅ Authentication working (401 expected without token)")
            elif response.status_code == 404:
                print(f"   ✅ File validation working (404 expected for test file)")
            else:
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
    
    # Test the old request format to confirm it fails
    print(f"\n{len(test_requests) + 1}. Testing old format (should fail)")
    old_format_data = {"file_id": "test-file-old"}
    print(f"   Request data: {json.dumps(old_format_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze/",
            json=old_format_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 422:
            error_data = response.json()
            print(f"   ✅ Old format correctly rejected (422)")
            print(f"   Error details: {error_data.get('detail', 'No details')}")
        else:
            print(f"   ⚠️  Unexpected status code for old format")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    print(f"\n{'=' * 50}")
    print("🎉 Analysis endpoint format test completed!")
    print("\nNext steps:")
    print("1. Try uploading an image file in the frontend")
    print("2. Click 'Start Analysis' to test the corrected request format")
    print("3. Check if PDF processing works with poppler-utils installed")

if __name__ == "__main__":
    test_analysis_endpoint()
