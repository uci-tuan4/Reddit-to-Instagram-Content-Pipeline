import os
from openai import OpenAI
import json

# Initialize OpenAI client
client = None

def initialize_openai():
    """Initialize the OpenAI client with API key from environment or config"""
    global client
    
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # If not in environment, check config file
    if not api_key:
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('openai', {}).get('api_key')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
            
    if api_key:
        client = OpenAI(api_key=api_key)
        return True
    return False

def optimize_caption(original_caption, subreddit, post_title, optimization_level='moderate'):
    """
    Generate an optimized Instagram caption based on the Reddit post
    
    Args:
        original_caption: Original caption text
        subreddit: Subreddit name
        post_title: Original Reddit post title
        optimization_level: 'light', 'moderate', or 'creative'
        
    Returns:
        Optimized caption string
    """
    if not client:
        if not initialize_openai():
            return original_caption
    
    # Set personality based on optimization level
    personality_map = {
        'light': "Make minimal improvements to grammar and clarity.",
        'moderate': "Make it engaging and Instagram-friendly while maintaining the original message.",
        'creative': "Transform this into a highly engaging, viral-worthy Instagram caption with personality."
    }
    
    personality = personality_map.get(optimization_level, personality_map['moderate'])
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an expert Instagram content creator specializing in optimizing Reddit content for Instagram. {personality}"},
                {"role": "user", "content": f"This is a Reddit post from r/{subreddit} with the title: '{post_title}'\n\nThe current caption is: '{original_caption}'\n\nCreate an optimized Instagram caption that will maximize engagement. Keep it under 2200 characters and include relevant hashtags."}
            ]
        )
        
        optimized_caption = completion.choices[0].message.content
        return optimized_caption
    
    except Exception as e:
        print(f"Error optimizing caption: {e}")
        return original_caption

def generate_hashtags(subreddit, post_title, caption, count=10):
    """
    Generate optimized hashtags for an Instagram post based on content
    
    Args:
        subreddit: Subreddit name
        post_title: Original Reddit post title
        caption: Post caption
        count: Number of hashtags to generate
        
    Returns:
        String of hashtags
    """
    if not client:
        if not initialize_openai():
            return "#viral #trending #reddit"
    
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at creating targeted Instagram hashtags that maximize reach and engagement."},
                {"role": "user", "content": f"Generate {count} optimized hashtags for an Instagram post converted from Reddit r/{subreddit}. The post title is '{post_title}' and the caption starts with '{caption[:100]}...' Return ONLY the hashtags without explanation, separated by spaces, including the # symbol."}
            ]
        )
        
        hashtags = completion.choices[0].message.content.strip()
        return hashtags
    
    except Exception as e:
        print(f"Error generating hashtags: {e}")
        return "#viral #trending #reddit"

def analyze_content_sentiment(post_title, caption):
    """
    Analyze sentiment and topics of the content to provide insights
    
    Args:
        post_title: Original Reddit post title
        caption: Post caption
        
    Returns:
        Dictionary with sentiment and topic analysis
    """
    if not client:
        if not initialize_openai():
            return {"sentiment": "neutral", "topics": ["general"], "engagement_prediction": "medium"}
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert social media content analyzer. Provide analysis in JSON format only."},
                {"role": "user", "content": f"Analyze this content for Instagram - Title: '{post_title}', Caption: '{caption}'. Return a JSON object with these keys: sentiment (positive, negative, neutral), topics (array of relevant topics), and engagement_prediction (high, medium, low)."}
            ],
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(completion.choices[0].message.content)
        return analysis
    
    except Exception as e:
        print(f"Error analyzing content: {e}")
        return {"sentiment": "neutral", "topics": ["general"], "engagement_prediction": "medium"} 