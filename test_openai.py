#!/usr/bin/env python3
"""
Simple test script to diagnose OpenAI API connectivity issues.
Run this to check if OpenAI APIs are accessible from your network.
"""

import os
import sys
from dotenv import load_dotenv

def test_openai_connection():
    """Test basic OpenAI API connectivity"""
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("❌ No OPENAI_API_KEY found in .env file")
        return False

    try:
        from openai import OpenAI
        print("✅ OpenAI package imported successfully")

        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client created successfully")

        # Test with a simple text-only request (no image)
        print("🔄 Testing API connectivity with simple request...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a more basic model for testing
            messages=[{"role": "user", "content": "Hello, test message"}],
            max_tokens=10
        )

        if response.choices[0].message.content:
            print("✅ OpenAI API connection successful!")
            print(f"Response: {response.choices[0].message.content}")
            return True
        else:
            print("❌ Empty response from OpenAI")
            return False

    except ImportError as e:
        print(f"❌ OpenAI package not installed: {e}")
        return False
    except Exception as e:
        error_msg = str(e).lower()
        if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
            print(f"❌ Network/Firewall issue: {e}")
            print("💡 This is likely a corporate firewall blocking OpenAI APIs")
        elif "authentication" in error_msg or "api key" in error_msg:
            print(f"❌ Authentication issue: {e}")
            print("💡 Check your OpenAI API key is valid")
        else:
            print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing OpenAI API Connectivity")
    print("=" * 40)

    success = test_openai_connection()

    print("\n" + "=" * 40)
    if success:
        print("✅ OpenAI API is accessible!")
        print("💡 If the main app still fails, try:")
        print("   - Using Gemini instead (more reliable)")
        print("   - Setting OPENAI_MODEL=gpt-4o-mini in .env")
    else:
        print("❌ OpenAI API is not accessible")
        print("💡 Try these solutions:")
        print("   1. Use Gemini API instead (select 'gemini' in the app)")
        print("   2. Check with your IT department about firewall restrictions")
        print("   3. Verify your OpenAI API key has sufficient credits")
        print("   4. Try a different network (home vs office)")

    sys.exit(0 if success else 1)