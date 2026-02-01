#!/usr/bin/env python3
"""
Test OpenRouter vision capabilities
"""
import os
import json
import base64
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

def test_openrouter_vision_models():
    """Test various vision models available through OpenRouter"""
    
    # Your OpenRouter API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return
    
    # Test image (using the same test image)
    test_image_path = "page1_img1.png"
    if not os.path.exists(test_image_path):
        print(f"❌ Test image not found: {test_image_path}")
        return
    
    # Read and encode image
    with open(test_image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    print("🔍 Testing OpenRouter Vision Models")
    print("=" * 50)
    
    # List of vision-capable models to test
    vision_models = [
        "openai/gpt-4-vision-preview",
        "openai/gpt-4-turbo",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "google/gemini-pro-vision",
        "meta-llama/llama-3.2-90b-vision-instruct",
        "mistralai/pixtral-12b",
        "qwen/qwen-vl-max"
    ]
    
    client = httpx.Client(
        base_url="https://openrouter.ai/api/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://localhost:3000",  # Your site URL
            "X-Title": "PDF Translator Test"  # Your app name
        }
    )
    
    results = {}
    
    for model in vision_models:
        print(f"\n🧪 Testing {model}")
        try:
            response = client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Extract all visible English text from this image and translate it to Russian. Return JSON format with original and translated text."
                            }
                        ]
                    }],
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"✅ Success: {content[:100]}...")
                results[model] = {
                    "status": "success",
                    "content": content,
                    "tokens": result.get('usage', {}).get('total_tokens', 0)
                }
            else:
                error_msg = response.text
                print(f"❌ Failed: {response.status_code} - {error_msg}")
                results[model] = {
                    "status": "failed",
                    "error": error_msg
                }
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results[model] = {
                "status": "error",
                "error": str(e)
            }
    
    # Save results
    with open("openrouter_vision_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    successful = sum(1 for r in results.values() if r["status"] == "success")
    print(f"Successful: {successful}/{len(vision_models)}")
    print(f"Results saved to: openrouter_vision_test_results.json")
    
    # Show successful models
    print("\n✅ WORKING MODELS:")
    for model, result in results.items():
        if result["status"] == "success":
            print(f"  • {model}")

if __name__ == "__main__":
    test_openrouter_vision_models()