from gradio_client import Client as GradioClient
_finbert_client=None
def _get_finbert_client():
    global _finbert_client
    if _finbert_client is None:
        _finbert_client = GradioClient("Sabarna6/FinBERT_FinancialSentimentAnalysis")
    return _finbert_client

def _analyze_sentiment(text: str) -> dict:
    try:
        client = _get_finbert_client()
        result = client.predict(text=text, api_name="/predict")

        # result is typically a dict like {"Positive": 0.08, "Negative": 0.14, "Neutral": 0.77}
        # or a string — print it once to confirm shape
        print(f"[FinBERT] raw result: {result}")
        (result)=result
        if isinstance(result, dict):
            print("HIii")
        
        print()
        top_label = max(result, key=result.get)
        return {
            "sentiment":  top_label,
            "confidence": round(result[top_label], 4),
        }

    except Exception as e:
        print(f"[FinBERT] {e}")
        return {"sentiment": "Neutral", "confidence": 0.0}

# print(_analyze_sentiment("Asia-Pacific News An Indian company is set to build a $2 billion AI hub with Nvidia’s GPUs and go public. Here’s what we know so far"))
reslt=({'Positive': 0.0671, 'Negative': 0.013, 'Neutral': 0.9199}, 'Neutral')
result = reslt[0]
print(result)
if isinstance(result, dict):
    print("HIii")
        

top_label = max(result, key=result.get)
res={ "sentiment":  top_label, "confidence": round(result[top_label], 4)   }
print(res)