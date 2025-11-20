"""
Enhanced intent-based chatbot for customer support.
Handles property-related queries flexibly across multiple scenarios.
Can be extended to use LLM APIs like OpenAI or Hugging Face.
"""

import re
from datetime import datetime
import random


# Property-related keywords for flexible matching
PROPERTY_KEYWORDS = ['property', 'properties', 'home', 'homes', 'house', 'houses', 'apartment', 'apartments', 'condo', 'condos', 'dwelling', 'real estate', 'listing', 'listings', 'residential']
LOCATION_KEYWORDS = ['location', 'area', 'neighborhood', 'district', 'street', 'boston', 'city', 'zone']
PRICE_KEYWORDS = ['price', 'cost', 'value', 'afford', 'budget', 'payment', 'rent', 'sale', 'sold', 'worth', 'expensive']
FEATURE_KEYWORDS = ['bedroom', 'bathroom', 'room', 'bed', 'bath', 'space', 'size', 'sqft', 'square feet', 'kitchen', 'yard', 'garage', 'basement']
BUYING_KEYWORDS = ['buy', 'purchase', 'sale', 'selling', 'sold', 'for sale', 'owner', 'seller', 'invest', 'investment']
RENTING_KEYWORDS = ['rent', 'rental', 'rentals', 'lease', 'tenant', 'landlord', 'monthly', 'renting']
QUALITY_KEYWORDS = ['quality', 'condition', 'verify', 'verified', 'authentic', 'architect', 'builder', 'artisan', 'trust', 'provenance', 'score']

# Intent patterns and responses
INTENTS = {
    'greeting': {
        'patterns': [r'\b(hi|hello|hey|greetings|hola|welcome)\b', r'\bhow are you\b', r'\bwhat\'s up\b'],
        'responses': [
            "Hello! 👋 Welcome to RealHome! I'm your AI assistant. How can I help you find your perfect property today?",
            "Hi there! 😊 I'm here to assist you with buying, renting, or learning more about properties.",
            "Welcome to RealHome! 🏠 What can I help you with today?",
            "Hey! 👋 Ready to explore properties? I'm here to answer any questions!"
        ]
    },
    
    'property_search_buy': {
        'patterns': [r'\b(find|search|looking for|show me|browse)\b.*\b(property|home|house|apartment|condo)\b.*\b(buy|sale|purchase)\b',
                     r'\b(want to buy|looking to buy|interested in buying)\b.*\b(property|home|house)\b',
                     r'\bproperties for sale\b', r'\bsell.*property\b', r'\bhomes? to buy\b'],
        'responses': [
            "Great! 🎯 I can help you find properties for sale. Visit our **Buy** page to browse available listings. You can filter by location, property type, price range, and more!",
            "Fantastic! 🏠 Head to the **Buy** section to explore properties for sale. Use our search filters to narrow down by location, size, price, and property type.",
            "Perfect! Let me direct you to our **Buy** page where you can browse all available properties for purchase with detailed information and photos!",
            "Excellent! 💰 Visit our **Buy** page to discover properties for sale. You can search by location, budget, and features. Found something you like? Use the Contact Agent button! 📞"
        ]
    },
    
    'property_search_rent': {
        'patterns': [r'\b(find|search|looking for|show me|browse)\b.*\b(property|home|house|apartment|condo|rentals?|rooms?)\b.*\b(rent|lease|rental)\b',
                     r'\b(want to rent|looking to rent|interested in renting)\b.*\b(property|home|apartment)\b',
                     r'\bproperties? to rent\b', r'\bapartments? for rent\b', r'\brental listings\b',
                     r'\bfind rentals\b', r'\brental search\b', r'\blooking for rentals\b'],
        'responses': [
            "Wonderful! 🔑 I can help you find rental properties! Visit our **Rent** page to browse available rental listings. Filter by location, property type, and monthly rent budget!",
            "Perfect! 🏘️ Head to the **Rent** section to explore rental properties. You'll find apartments, homes, and more with all the details you need!",
            "Great! 🏠 Check out our **Rent** page for a variety of rental options. You can search by location, size, and price to find the perfect place!",
            "Excellent choice! 💎 Visit our **Rent** page to find rental properties that match your needs. Browse, compare, and contact landlords directly! 📞"
        ]
    },
    
    'property_details': {
        'patterns': [r'\b(what is|tell me about|more info on|details of|show me)\b.*\b(property|home|listing)\b',
                     r'\b(bedroom|bathroom|square|size|features?)\b.*\b(property|home|apartment)\b',
                     r'\b(what can you tell me about this|how big is|what features)\b'],
        'responses': [
            "Each property listing shows key details like number of bedrooms/bathrooms, square footage, crime rate, and school ratings! 📊 Click on any property to see full details and photos.",
            "I'd love to help! 🔍 On our **Buy** or **Rent** pages, each property card displays essential info. Click to view complete details including address, photos, and Provenance Score! ✨",
            "Property information includes location, size, features, pricing, and our Provenance verification score! 🏡 Visit the listing page for comprehensive details and contact options.",
            "You can see details like rooms, area, neighborhood info, and verification status on each listing! 📋 Click any property to explore more!"
        ]
    },
    
    'valuation': {
        'patterns': [r'\b(estimate|estimate.*value|value.*property|what.*worth|price.*estimate)\b',
                     r'\bhow much (is|are|would)\b.*\b(property|home|this|worth|sell for)\b',
                     r'\b(appraise|valuation|fair market|estimated price)\b',
                     r'\bwhat.*price.*property\b'],
        'responses': [
            "Excellent question! 💰 Use our **Value Estimator** tool to get an AI-powered estimate of property values. It analyzes key features like location, size, and neighborhood data!",
            "Our **Value Estimator** uses machine learning to provide fair market estimates! 🤖 Enter property details like rooms, location, and other features to get a valuation.",
            "Want to know a property's value? 📈 Try our **Value Estimator** page! It gives you an estimated price based on current market trends and property characteristics.",
            "Our advanced ML model estimates property values based on market data! 💻 Use the **Value Estimator** to get instant price predictions for any property!"
        ]
    },
    
    'contact_agent': {
        'patterns': [r'\b(contact|reach|speak|talk to|message|call)\b.*\b(agent|seller|owner|landlord)\b',
                     r'\b(want to|how to)\b.*\b(contact|reach)\b.*\b(property owner|seller|agent)\b',
                     r'\bhow can i.*\b(connect|message|reach)\b',
                     r'\b(inquiry|inquire|interested in|make an offer)\b'],
        'responses': [
            "Perfect! 📞 On any property listing, click the **Contact Agent** button to send a message or inquiry. The agent will get back to you quickly!",
            "Great! 💬 Each property has a **Contact Agent** option. Click it to send your inquiry, ask questions, or express interest. Easy and direct!",
            "You can reach out directly from the property listing! 📧 Use the **Contact Agent** button to message agents about any property you're interested in.",
            "Simple! 🎯 Find a property you like and click **Contact Agent**. You can ask questions, request more info, or schedule a viewing!"
        ]
    },
    
    'verification_quality': {
        'patterns': [
                     # catch quality/verification keywords anywhere, or property+quality in any order
                     r'\b(quality|verification|verify|verified|provenance|authenticity|trust|score|badge)\b',
                     r'\b(property|home|listing).*(quality|verification|verify|verified|provenance)\b',
                     r'\b(quality|verification|verify|verified|provenance).*(property|home|listing)\b',
                     r'\b(verify|verified|quality|authenticity|trust|reliable)\b.*\b(property|home|builder|architect)\b',
                     r'\bhow.*\b(know|ensure)\b.*\b(quality|authentic|verified)\b',
                     r'\b(provenance|verified|badge|score)\b',
                     r'\b(architect|builder|artisan).*(verified|authentic|quality)\b'],
        'responses': [
            "Great question! 🔐 Our **Provenance Score** shows property quality verification. It includes verified contributions from architects, builders, and artisans. Higher scores = more verified quality!",
            "We ensure quality through our **Provenance System**! ✅ Each property shows verified architect, builder, and artisan contributions with documentation. Check the Provenance Score on listings!",
            "Transparency is key! 🏆 Properties display a **Provenance Score** indicating verified quality contributors. See who worked on the property and their credentials!",
            "Our verification system tracks authentic contributions! 📜 Architects, builders, and artisans are verified and documented. Look for the Provenance Score on each property!"
        ]
    },
    
    'pricing_features': {
        'patterns': [r'\b(how much|what.*cost|price range|affordable)\b',
                     r'\b(cheap|expensive|budget friendly|luxury)\b.*\b(property|home)\b',
                     r'\b(under|over|between)\b.*\b(price|cost)\b'],
        'responses': [
            "Properties come in all price ranges! 💵 Use our search filters on **Buy** or **Rent** pages to narrow by budget. You'll find options from affordable to luxury!",
            "Great! 🏠 Our listings range from budget-friendly to premium properties. Filter by price on the **Buy** or **Rent** pages to see what fits your budget!",
            "We have properties for every budget! 💰 Use the price range filter to find exactly what you're looking for. Browse our full inventory!",
            "Price ranges vary widely! 📊 Visit **Buy** or **Rent** pages and use filters to find properties within your budget. Check all prices and details!"
        ]
    },
    
    'account_login': {
        'patterns': [r'\b(sign up|register|create.*account|new account|join)\b',
                     r'\b(login|log in|sign in|account)\b',
                     r'\b(password|username|profile)\b',
                     r'\b(how do i|can i)\b.*\b(create|sign up|login)\b'],
        'responses': [
            "Easy! 🚀 Click the **Sign Up** button to create a free RealHome account. This lets you save favorites, get alerts, and contact agents directly!",
            "Quick process! ⚡ Head to **Sign Up** to register. You'll get access to saved properties, personalized alerts, and agent communications!",
            "Simple registration! 📝 Use the **Sign Up** page to create your account in minutes. Then you can favorite properties and contact agents anytime!",
            "Ready to join? 🎯 Visit the **Sign Up** page to register. Already have an account? Click **Login** to access your saved properties!"
        ]
    },
    
    'navigation': {
        'patterns': [r'\b(where|how to find|how to get to|navigate to|go to)\b.*\b(buy|rent|about|support|profile)\b',
                     r'\b(what\'s|what is)\b.*(buy page|rent page|support page)',
                     r'\bmenu|navigation\b'],
        'responses': [
            "Navigation is easy! 🗺️ Use our main menu to access **Buy**, **Rent**, **About Us**, **Customer Support**, and **Profile**. Everything you need is just a click away!",
            "Simple! 📍 Click on **Buy** to browse properties for sale, **Rent** for rental listings, **About Us** for info, and **Support** if you need help!",
            "Our site is easy to navigate! 🧭 Look at the top menu for **Buy**, **Rent**, **About**, **Support**, and your **Profile**. Choose what you need!",
            "Quick navigation! ⬆️ Top menu has all pages: **Buy**, **Rent**, **About Us**, **Customer Support**, and **Profile**. Find what you're looking for easily!"
        ]
    },
    
    'general_help': {
        'patterns': [r'\b(help|support|issue|problem|bug|error)\b',
                     r'\b(something.*wrong|not working|having trouble)\b',
                     r'\b(can you help|what should i do|stuck)\b'],
        'responses': [
            "I'm here to help! 💪 Tell me more about what you need, and I'll guide you. If it's complex, I can connect you with our support team!",
            "No problem! 🤝 Describe what you're looking for or what issue you're having, and I'll help or escalate to our support team if needed.",
            "Happy to assist! 😊 What's your question? Whether it's about searching, verifying, or anything else, I'm ready to help!",
            "Let me help! 🆘 Tell me what you need, and I'll do my best to solve it or connect you with the right team!"
        ]
    },
    
    'goodbye': {
        'patterns': [r'\b(bye|goodbye|see you|thanks|thank you|that\'s all|no thanks)\b',
                     r'\b(quit|exit|close|done|finished)\b', r'\b(take care|cheers)\b'],
        'responses': [
            "Thanks for visiting RealHome! 👋 Good luck with your property search. Come back anytime!",
            "Goodbye! 🏠 Feel free to return if you have more questions. Happy house hunting! 🎉",
            "Thanks for chatting! 😊 Don't hesitate to reach out. Enjoy exploring properties on RealHome!",
            "Have a great day! 👋 See you next time you visit RealHome. Best of luck! 🍀"
        ]
    }
}


def extract_keywords(user_input: str) -> dict:
    """
    Extract relevant keywords from user input to provide context.
    """
    user_lower = user_input.lower()
    keywords = {
        'property': any(kw in user_lower for kw in PROPERTY_KEYWORDS),
        'location': any(kw in user_lower for kw in LOCATION_KEYWORDS),
        'price': any(kw in user_lower for kw in PRICE_KEYWORDS),
        'features': any(kw in user_lower for kw in FEATURE_KEYWORDS),
        'buying': any(kw in user_lower for kw in BUYING_KEYWORDS),
        'renting': any(kw in user_lower for kw in RENTING_KEYWORDS),
        'quality': any(kw in user_lower for kw in QUALITY_KEYWORDS),
    }
    return keywords


def match_intent(user_input: str) -> tuple:
    """
    Match user input to an intent and return (intent_name, response).
    Enhanced to handle property-related queries more flexibly.
    """
    user_input = user_input.lower().strip()
    
    # Extract keywords for context
    keywords = extract_keywords(user_input)
    
    # Prioritize property-related intents if keywords match
    if keywords['property']:
        if keywords['buying']:
            # User asking about buying properties
            for pattern in INTENTS['property_search_buy']['patterns']:
                if re.search(pattern, user_input):
                    responses = INTENTS['property_search_buy']['responses']
                    return 'property_search_buy', random.choice(responses)
        
        if keywords['renting']:
            # User asking about renting properties
            for pattern in INTENTS['property_search_rent']['patterns']:
                if re.search(pattern, user_input):
                    responses = INTENTS['property_search_rent']['responses']
                    return 'property_search_rent', random.choice(responses)
        
        # Prioritize quality/verification questions when both property and quality keywords appear
        if keywords['quality']:
            for pattern in INTENTS['verification_quality']['patterns']:
                if re.search(pattern, user_input):
                    responses = INTENTS['verification_quality']['responses']
                    return 'verification_quality', random.choice(responses)

        if keywords['price'] or keywords['features'] or keywords['location']:
            # User asking about property details
            for pattern in INTENTS['property_details']['patterns']:
                if re.search(pattern, user_input):
                    responses = INTENTS['property_details']['responses']
                    return 'property_details', random.choice(responses)
        
        # Generic property question
        if keywords['price']:
            for pattern in INTENTS['pricing_features']['patterns']:
                if re.search(pattern, user_input):
                    responses = INTENTS['pricing_features']['responses']
                    return 'pricing_features', random.choice(responses)
    
    # Try to match all intents
    for intent_name, intent_data in INTENTS.items():
        for pattern in intent_data['patterns']:
            if re.search(pattern, user_input):
                responses = intent_data['responses']
                return intent_name, random.choice(responses)
    
    # Default response if no intent matched
    default_responses = [
        "That's a great question! 🤔 I'm here to help with property search, buying, renting, valuation, verification, and more. Could you provide more details? 🏠",
        "Interesting! 💭 I specialize in helping with properties. Are you looking to buy, rent, or learn more about a specific property? Tell me more!",
        "I'm not entirely sure, but I'm here to help! 📚 Ask me about buying properties, renting, valuations, or anything property-related!",
        "Great question! 🎯 I can better help if you give me more context. Are you interested in buying, renting, or learning about property details? 🏡"
    ]
    return 'unknown', random.choice(default_responses)


def get_chatbot_response(user_message: str) -> dict:
    """
    Process user message and return a response.
    """
    if not user_message or len(user_message.strip()) == 0:
        return {
            'status': 'error',
            'message': 'Please enter a message.',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    intent, response = match_intent(user_message)
    
    return {
        'status': 'ok',
        'intent': intent,
        'message': response,
        'user_input': user_message,
        'timestamp': datetime.utcnow().isoformat()
    }
